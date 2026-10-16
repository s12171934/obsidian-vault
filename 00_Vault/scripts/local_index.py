#!/usr/bin/env python3
"""Build the git-ignored _index.md of each local-only domain from its tracked rules/.

    python3 00_Vault/scripts/local_index.py          show what would change
    python3 00_Vault/scripts/local_index.py apply    write the changes

For each local domain (10_Projects, 30_Automations, 50_Knowledge):
- the 「규칙」 section lists every rules/*.md note as `- [[<title>]] — <first sentence of its summary>`;
- a missing _index.md is created in the minimal form (summary, 상위, 규칙). The summary is the domain's
  "담는 것" cell in the 최상위 구성 table of 00_Vault/rules/폴더 구조 규칙.md, so that table stays the source;
- an existing _index.md keeps every other section (e.g. 「목록」); only 「규칙」 is replaced, and `updated` is
  bumped when it changes.
A missing CHANGE_LOG.md is created as an empty log. Standard library only.
"""
import datetime
import os
import re
import sys

LOCAL_DOMAINS = ["10_Projects", "30_Automations", "50_Knowledge"]
VAULT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
STRUCTURE = os.path.join(VAULT, "00_Vault", "rules", "폴더 구조 규칙.md")
TODAY = datetime.date.today().isoformat()
APPLY = len(sys.argv) > 1 and sys.argv[1] == "apply"
if len(sys.argv) > 1 and sys.argv[1] not in ("apply", "check"):
    sys.exit("usage: local_index.py [check|apply]")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text, what):
    print(("  + " if APPLY else "  ~ ") + what)
    if APPLY:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)


def front(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    return dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M)) if m else {}


def first_sentence(text):
    body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
    m = re.search(r"^>\s*(.+)$", body, re.M)
    if not m:
        return ""
    line = m.group(1).strip()
    s = re.match(r"(.+?[다요]\.)(\s|$)", line)
    return s.group(1) if s else line


def domain_summary(domain):
    for line in read(STRUCTURE).splitlines():
        if line.startswith(f"| `{domain}/` |"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            return f"{cells[-1]} (로컬 전용, git 무시 — `rules/` 만 추적)"
    return f"{domain} 도메인 (로컬 전용, git 무시 — `rules/` 만 추적)"


def rules_section(domain):
    rdir = os.path.join(VAULT, domain, "rules")
    items = []
    if os.path.isdir(rdir):
        for name in sorted(os.listdir(rdir)):
            if name.endswith(".md"):
                text = read(os.path.join(rdir, name))
                title = front(text).get("title") or name[:-3]
                desc = first_sentence(text)
                items.append(f"- [[{title}]]" + (f" — {desc}" if desc else ""))
    return "## 규칙\n\n" + "\n".join(items) + "\n" if items else ""


def build(domain):
    print(f"[{domain}]")
    ddir = os.path.join(VAULT, domain)
    if not os.path.isdir(ddir):
        print(("  + " if APPLY else "  ~ ") + f"create {domain}/")
        if APPLY:
            os.makedirs(ddir)
    path = os.path.join(ddir, "_index.md")
    section = rules_section(domain)
    if not os.path.exists(path):
        title = f"{domain} 인덱스"
        text = (f"---\ntitle: {title}\ncreated: {TODAY}\nupdated: {TODAY}\ntags: [meta]\nsource: ai\n---\n\n"
                f"# {title}\n\n> {domain_summary(domain)}\n\n상위: [[_Home]]\n\n{section}")
        write(path, text, f"create {domain}/_index.md")
        return
    old = read(path)
    m = re.search(r"^## 규칙\n.*?(?=^## |\Z)", old, re.M | re.S)
    if m:
        new = old[:m.start()] + section + ("\n" if section and old[m.end():] else "") + old[m.end():]
    else:
        up = re.search(r"^상위:.*\n", old, re.M)
        at = up.end() if up else len(old)
        new = old[:at] + ("\n" + section if section else "") + old[at:]
    new = re.sub(r"\n{3,}", "\n\n", new)
    if new == old:
        print("  = up to date")
        return
    new = re.sub(r"^updated: .*$", f"updated: {TODAY}", new, count=1, flags=re.M)
    write(path, new, f"update 「규칙」 in {domain}/_index.md")


for d in LOCAL_DOMAINS:
    build(d)

log = os.path.join(VAULT, "CHANGE_LOG.md")
print("[CHANGE_LOG.md]")
if os.path.exists(log):
    print("  = exists")
else:
    write(log, (f"---\ntitle: CHANGE_LOG\ncreated: {TODAY}\nupdated: {TODAY}\ntags: [meta]\nsource: ai\n---\n\n"
                "# CHANGE_LOG\n\n> 로컬 전용 노트의 개정 이력을 모은 단일 로그. 형식은 [[변경 이력 규칙]] 이 정한다.\n"),
          "create empty CHANGE_LOG.md")
if not APPLY:
    print("(check only — run with 'apply' to make these changes)")
