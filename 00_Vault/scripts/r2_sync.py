#!/usr/bin/env python3
"""볼트 Attachments/ 를 Cloudflare R2 로 이관하는 도구.

표준 라이브러리만 사용한다 (boto3·rclone·wrangler 불필요). S3 SigV4 서명을 직접 만든다.

비밀이 아닌 설정(버킷·공개 URL·키 접두사)은 로컬 전용 `30_Automations/첨부 R2/config.json` 에 둔다
(환경 변수 VAULT_R2_CONFIG 로 바꿀 수 있다). 형식:

  {"bucket": "<버킷 이름>", "public_base_url": "https://<커스텀 도메인>", "key_prefix": "attachments"}

자격증명은 업로더 플러그인(S3 Image Sync)의 설정을 그대로 읽는다 — 플러그인이 이미
`.obsidian/plugins/images-uploader/data.json` 에 갖고 있으므로, 별도 사본을 만들면
같은 비밀의 노출면만 넓어진다. 플러그인을 쓰지 않는 환경을 위해 Keychain 도 지원한다:

  security add-generic-password -s obsidian-r2 -a default \
    -w '{"account_id":"...","access_key_id":"...","secret_access_key":"..."}'

사용법:
  r2_sync.py plan                 업로드 대상과 목적지 URL 을 표로 출력 (네트워크 접근 없음)
  r2_sync.py upload [--dry-run]   R2 로 업로드하고 HEAD 로 크기를 검증
  r2_sync.py verify               로컬 파일과 R2 객체의 존재·크기 대조
  r2_sync.py delete-local         verify 를 통과한 파일만 로컬에서 삭제
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import hmac
import json
import mimetypes
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VAULT_ROOT = SCRIPT_DIR.parents[1]  # <vault>/00_Vault/scripts
ATTACHMENTS = VAULT_ROOT / "Attachments"
CONFIG_PATH = Path(os.environ.get("VAULT_R2_CONFIG") or VAULT_ROOT / "30_Automations" / "첨부 R2" / "config.json")
PLUGIN_DATA = VAULT_ROOT / ".obsidian/plugins/images-uploader/data.json"

KEYCHAIN_SERVICE = "obsidian-r2"
KEYCHAIN_ACCOUNT = "default"

REGION = "auto"
SERVICE = "s3"
UNSIGNED_SKIP = {".DS_Store", "._.DS_Store"}


# --------------------------------------------------------------------------- 설정

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit(f"설정 파일이 없다: {CONFIG_PATH}\n  이 스크립트 첫 주석의 형식대로 만든다.")
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    missing = [k for k in ("bucket", "public_base_url") if not cfg.get(k)]
    if missing:
        sys.exit(f"config.json 에 값이 비어 있다: {', '.join(missing)}")
    cfg.setdefault("key_prefix", "attachments")
    cfg["public_base_url"] = cfg["public_base_url"].rstrip("/")
    return cfg


def _creds_from_keychain() -> tuple[str, str, str] | None:
    try:
        raw = subprocess.run(
            ["security", "find-generic-password",
             "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT, "-w"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        blob = json.loads(raw)
        return blob["account_id"], blob["access_key_id"], blob["secret_access_key"]
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
        return None


def _creds_from_plugin() -> tuple[str, str, str] | None:
    """업로더 플러그인의 설정에서 읽는다. 엔드포인트 호스트의 첫 라벨이 계정 ID 다."""
    if not PLUGIN_DATA.exists():
        return None
    try:
        s3 = json.loads(PLUGIN_DATA.read_text(encoding="utf-8"))["s3"]
        host = urllib.parse.urlparse(s3["endpoint"]).hostname or ""
        account_id = host.split(".")[0]
        if not (account_id and s3.get("accessKeyId") and s3.get("secretAccessKey")):
            return None
        return account_id, s3["accessKeyId"], s3["secretAccessKey"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def load_credentials() -> tuple[str, str, str]:
    for source, fn in (("Keychain", _creds_from_keychain), ("플러그인 설정", _creds_from_plugin)):
        creds = fn()
        if creds:
            print(f"[자격증명] {source}", file=sys.stderr)
            return creds
    sys.exit(
        "자격증명을 찾지 못했다. 둘 중 하나가 있어야 한다:\n"
        f"  1) {PLUGIN_DATA} 의 s3 설정 (업로더 플러그인)\n"
        "  2) security add-generic-password -s obsidian-r2 -a default -w "
        "'{\"account_id\":\"...\",\"access_key_id\":\"...\",\"secret_access_key\":\"...\"}'"
    )


# --------------------------------------------------------------------------- SigV4

def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret: str, datestamp: str) -> bytes:
    k = _sign(f"AWS4{secret}".encode("utf-8"), datestamp)
    k = _sign(k, REGION)
    k = _sign(k, SERVICE)
    return _sign(k, "aws4_request")


def _encode_path(path: str) -> str:
    """정규 요청용 URI 인코딩. 슬래시는 그대로 두고 나머지는 RFC3986 unreserved 만 남긴다."""
    return "/".join(urllib.parse.quote(seg, safe="~") for seg in path.split("/"))


def signed_request(cfg: dict, creds: tuple[str, str, str], method: str, key: str,
                   body: bytes = b"", content_type: str | None = None) -> urllib.request.Request:
    account_id, access_key, secret_key = creds
    host = f"{account_id}.r2.cloudflarestorage.com"
    canonical_uri = _encode_path(f"/{cfg['bucket']}/{key}")

    now = dt.datetime.now(dt.timezone.utc)
    amzdate = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now.strftime("%Y%m%d")
    payload_hash = hashlib.sha256(body).hexdigest()

    headers = {
        "host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amzdate,
    }
    if content_type:
        headers["content-type"] = content_type

    signed_headers = ";".join(sorted(headers))
    canonical_headers = "".join(f"{k}:{headers[k]}\n" for k in sorted(headers))
    canonical_request = "\n".join([
        method, canonical_uri, "", canonical_headers, signed_headers, payload_hash,
    ])

    scope = f"{datestamp}/{REGION}/{SERVICE}/aws4_request"
    string_to_sign = "\n".join([
        "AWS4-HMAC-SHA256", amzdate, scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    ])
    signature = hmac.new(
        _signing_key(secret_key, datestamp), string_to_sign.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    headers["Authorization"] = (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    req = urllib.request.Request(
        f"https://{host}{canonical_uri}", data=body or None, method=method
    )
    for k, v in headers.items():
        req.add_header(k, v)
    return req


def call(req: urllib.request.Request) -> tuple[int, dict, bytes]:
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


# --------------------------------------------------------------------------- 대상 수집

def local_files(warn_empty: bool = True) -> list[Path]:
    """업로드 후보. 0바이트 파일은 손상으로 보고 제외한다 — 올린 뒤 로컬을 지우면
    깨진 링크가 고착되고 복구 단서가 사라진다."""
    if not ATTACHMENTS.is_dir():
        sys.exit(f"{ATTACHMENTS} 가 없다.")
    files, empty = [], []
    for p in sorted(ATTACHMENTS.rglob("*")):
        if not p.is_file() or p.name in UNSIGNED_SKIP:
            continue
        (empty if p.stat().st_size == 0 else files).append(p)
    if empty and warn_empty:
        print("[경고] 0바이트라 제외한다 (원본 복구가 먼저다):", file=sys.stderr)
        for p in empty:
            print(f"        {p.relative_to(VAULT_ROOT)}", file=sys.stderr)
        print(file=sys.stderr)
    return files


def object_key(cfg: dict, path: Path) -> str:
    rel = path.relative_to(ATTACHMENTS).as_posix()
    prefix = cfg["key_prefix"].strip("/")
    return f"{prefix}/{rel}" if prefix else rel


def public_url(cfg: dict, key: str) -> str:
    return f"{cfg['public_base_url']}/{urllib.parse.quote(key, safe='/')}"


# --------------------------------------------------------------------------- 명령

def cmd_plan(cfg: dict, _creds, _args) -> int:
    files = local_files()
    total = 0
    for p in files:
        key = object_key(cfg, p)
        size = p.stat().st_size
        total += size
        print(f"{size:>9,}  {p.relative_to(VAULT_ROOT)}\n           -> {public_url(cfg, key)}")
    print(f"\n{len(files)}개 · {total:,} bytes")
    return 0


def cmd_upload(cfg: dict, creds, args) -> int:
    files = local_files()
    failed = 0
    for p in files:
        key = object_key(cfg, p)
        body = p.read_bytes()
        ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        if args.dry_run:
            print(f"[dry-run] PUT {key} ({len(body):,} bytes, {ctype})")
            continue
        status, _, resp = call(signed_request(cfg, creds, "PUT", key, body, ctype))
        if status not in (200, 201):
            print(f"[FAIL {status}] {key}\n  {resp[:400].decode('utf-8', 'replace')}")
            failed += 1
            continue
        hstatus, hheaders, _ = call(signed_request(cfg, creds, "HEAD", key))
        remote = int(hheaders.get("Content-Length", -1))
        if hstatus != 200 or remote != len(body):
            print(f"[VERIFY FAIL] {key} — HEAD {hstatus}, {remote} != {len(body)}")
            failed += 1
            continue
        print(f"[ok] {key} ({len(body):,} bytes)\n     {public_url(cfg, key)}")
    return 1 if failed else 0


def cmd_verify(cfg: dict, creds, _args) -> int:
    files = local_files()
    bad = 0
    for p in files:
        key = object_key(cfg, p)
        status, headers, _ = call(signed_request(cfg, creds, "HEAD", key))
        size = p.stat().st_size
        remote = int(headers.get("Content-Length", -1))
        if status == 200 and remote == size:
            print(f"[ok]   {key}")
        else:
            print(f"[MISMATCH] {key} — HEAD {status}, remote={remote}, local={size}")
            bad += 1
    print(f"\n{len(files) - bad}/{len(files)} 일치")
    return 1 if bad else 0


def cmd_delete_local(cfg: dict, creds, args) -> int:
    files = local_files()
    ok: list[Path] = []
    for p in files:
        key = object_key(cfg, p)
        status, headers, _ = call(signed_request(cfg, creds, "HEAD", key))
        if status == 200 and int(headers.get("Content-Length", -1)) == p.stat().st_size:
            ok.append(p)
        else:
            print(f"[skip] 검증 실패라 남긴다: {p.relative_to(VAULT_ROOT)}")
    if not ok:
        print("삭제할 대상이 없다.")
        return 0
    for p in ok:
        if args.dry_run:
            print(f"[dry-run] rm {p.relative_to(VAULT_ROOT)}")
        else:
            p.unlink()
            print(f"[rm] {p.relative_to(VAULT_ROOT)}")
    if not args.dry_run:
        for d in sorted((d for d in ATTACHMENTS.rglob("*") if d.is_dir()), reverse=True):
            if not any(d.iterdir()):
                d.rmdir()
                print(f"[rmdir] {d.relative_to(VAULT_ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Attachments/ → Cloudflare R2 이관")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name, fn, needs_dry in (
        ("plan", cmd_plan, False),
        ("upload", cmd_upload, True),
        ("verify", cmd_verify, False),
        ("delete-local", cmd_delete_local, True),
    ):
        sp = sub.add_parser(name)
        if needs_dry:
            sp.add_argument("--dry-run", action="store_true")
        sp.set_defaults(func=fn)
    args = parser.parse_args()
    if not hasattr(args, "dry_run"):
        args.dry_run = False

    cfg = load_config()
    creds = ("", "", "") if args.func is cmd_plan else load_credentials()
    return args.func(cfg, creds, args)


if __name__ == "__main__":
    sys.exit(main())
