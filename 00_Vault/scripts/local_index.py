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
A missing CHANGE_LOG.md is created as an empty log.

Knowledge classification (the local, git-ignored 50_Knowledge/지식 분류표.md is the registry):
- a missing registry is created with only the 대분류 rows, taken from the tracked domain list in
  00_Vault/rules/노트 작성 규칙.md §3; 50_Knowledge/_index.md gets a 「목록」 link to it;
- every 50_Knowledge folder must be `<code> <name>` of a registered class (or `<code>.00 일반`), nested
  D / D.AA / D.AA.SS, and every note other than _index.md must be `D.AA.SS.NNN <title>.md` inside the
  folder of its code, with `title` equal to the file name and no duplicate numbers;
- its domain/area/topic tags must be exactly the ones its number implies — `apply` rewrites them;
- domain/area/topic tags anywhere in the vault must be registered and come with their parent tags,
  and the registry itself must be consistent.
Problems are printed as `  ! …`; only the 50 tag rewrite is fixed automatically. Standard library only.
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
# ---- knowledge classification (50_Knowledge) ----
KNOW = os.path.join(VAULT, "50_Knowledge")
CLASS_TABLE = os.path.join(KNOW, "지식 분류표.md")
NOTE_RULE = os.path.join(VAULT, "00_Vault", "rules", "노트 작성 규칙.md")
CLASS_AXES = ("domain/", "area/", "topic/")
NUM_RE = re.compile(r"^(\d\.\d\d\.\d\d\.\d{3}) (.+)\.md$")


def load_classes():
    classes, problems = {}, []
    if not os.path.exists(CLASS_TABLE):
        return classes, ["missing 50_Knowledge/지식 분류표.md"]
    for line in read(CLASS_TABLE).splitlines():
        m = re.match(r"^\| `([0-9.]+)` \| ([^|]+?) \| `([^`]+)` \|", line)
        if not m:
            continue
        code, name, tag = m.groups()
        depth = code.count(".")
        axis = CLASS_AXES[depth] if depth < 3 else None
        if not re.fullmatch(r"\d(\.\d\d){0,2}", code) or code.endswith(".00"):
            problems.append(f"분류표: bad code {code}")
        elif not tag.startswith(axis):
            problems.append(f"분류표: {code} tag {tag} should start with {axis}")
        elif depth and code.rsplit(".", 1)[0] not in classes:
            problems.append(f"분류표: {code} has no parent {code.rsplit('.', 1)[0]}")
        elif code in classes or tag in [c[1] for c in classes.values()]:
            problems.append(f"분류표: duplicate code or tag at {code} ({tag})")
        else:
            classes[code] = (name, tag)
    return classes, problems


def expected_tags(classes, number):
    d, aa, ss, _ = number.split(".")
    tags = [classes[d][1]]
    if aa != "00":
        tags.append(classes[f"{d}.{aa}"][1])
        if ss != "00":
            tags.append(classes[f"{d}.{aa}.{ss}"][1])
    return tags


def folder_code(classes, name, parent):
    """Return the code of a class folder name, or None if it is not a valid child of parent."""
    m = re.match(r"^(\d(?:\.\d\d){0,2}) (.+)$", name)
    if not m:
        return None
    code, label = m.groups()
    if parent is None and "." in code or parent is not None and code.rsplit(".", 1)[0] != parent:
        return None
    if code in classes:
        return code if classes[code][0] == label else None
    return code if code.endswith(".00") and label == "일반" else None


def check_knowledge(classes):
    problems, fixes = [], []
    if not os.path.isdir(KNOW):
        return problems, fixes
    numbers = {}
    for root, dirs, files in os.walk(KNOW):
        rel = os.path.relpath(root, KNOW)
        parts = [] if rel == "." else rel.split(os.sep)
        if parts[:1] == ["rules"]:
            dirs[:] = []
            continue
        codes, parent = [], None
        for part in parts:
            c = folder_code(classes, part, parent)
            if c is None:
                break
            codes.append(c)
            parent = c
        if len(codes) < len(parts) or len(parts) > 3:
            problems.append(f"unregistered or misplaced folder: 50_Knowledge/{rel}")
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not d.startswith(".") and not (not parts and d == "rules")]
        for f in sorted(files):
            if not f.endswith(".md") or f == "_index.md" or (not parts and f == "_index.md"):
                continue
            path = os.path.join(root, f)
            relf = os.path.relpath(path, VAULT)
            m = NUM_RE.match(f)
            if not parts and f == "지식 분류표.md":
                continue
            if not m or len(parts) != 3 or not m.group(1).startswith(codes[-1] + "."):
                problems.append(f"name or place does not match a class number: {relf}")
                continue
            num = m.group(1)
            if num in numbers:
                problems.append(f"duplicate number {num}: {relf} and {numbers[num]}")
            numbers[num] = relf
            text = read(path)
            if front(text).get("title") != f[:-3]:
                problems.append(f"title differs from file name: {relf}")
            want = expected_tags(classes, num)
            tm = re.search(r"^tags:\s*\[(.*)\]\s*$", text, re.M)
            if not tm:
                problems.append(f"no one-line tags: [...] in {relf}")
                continue
            tags = [x.strip() for x in tm.group(1).split(",") if x.strip()]
            have = [x for x in tags if x.startswith(CLASS_AXES)]
            if have != want:
                rest = [x for x in tags if not x.startswith(CLASS_AXES)]
                new = text[:tm.start()] + "tags: [" + ", ".join(want + rest) + "]" + text[tm.end():]
                fixes.append((path, new, f"retag {relf}: {have} -> {want}"))
    return problems, fixes


def check_vault_tags(classes):
    registered = {c[1] for c in classes.values()}
    parent_of = {tag: classes[code.rsplit(".", 1)[0]][1] for code, (_, tag) in classes.items() if "." in code}
    problems = []
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(root, f)
            tm = re.search(r"^tags:\s*\[(.*)\]\s*$", read(path), re.M)
            if not tm:
                continue
            tags = [x.strip() for x in tm.group(1).split(",")]
            for x in tags:
                if not x.startswith(CLASS_AXES) or "<" in x:
                    continue
                if x not in registered:
                    problems.append(f"unregistered tag {x}: {os.path.relpath(path, VAULT)}")
                elif x in parent_of and parent_of[x] not in tags:
                    problems.append(f"{x} without its parent {parent_of[x]}: {os.path.relpath(path, VAULT)}")
    return problems


def ensure_registry():
    if os.path.exists(CLASS_TABLE):
        return
    line = next((l for l in read(NOTE_RULE).splitlines() if l.startswith("- 등록된 대분류")), "")
    rows = "".join(f"| `{c}` | {n} | `domain/{n}` |\n" for n, c in re.findall(r"`domain/([^`]+)`\((\d)\)", line))
    text = (f"---\ntitle: 지식 분류표\ncreated: {TODAY}\nupdated: {TODAY}\ntags: [meta]\nsource: ai\n---\n\n"
            "# 지식 분류표\n\n> 볼트 지식 분류의 등록부다 (로컬 전용, git 무시). 번호 체계와 등록·변경 절차는 "
            "[[50_Knowledge 범위 규칙]], 대분류 목록은 [[노트 작성 규칙]] §3 이 정한다.\n\n"
            "## 분류\n\n| 코드 | 이름 | 태그 |\n| --- | --- | --- |\n" + rows + "\n## 폐지 코드\n\n- 없음\n")
    write(CLASS_TABLE, text, "create 50_Knowledge/지식 분류표.md (대분류 rows only)")


def ensure_registry_link():
    path = os.path.join(KNOW, "_index.md")
    if not os.path.exists(path) or "[[지식 분류표]]" in read(path):
        return
    old = read(path)
    item = "- [[지식 분류표]] — 분류 코드·이름·태그 등록부\n"
    m = re.search(r"^## 목록\n\n?", old, re.M)
    new = old[:m.end()] + item + old[m.end():] if m else old.rstrip("\n") + "\n\n## 목록\n\n" + item
    write(path, new, "link 지식 분류표 from 50_Knowledge/_index.md 「목록」")


print("[50_Knowledge classification]")
ensure_registry()
ensure_registry_link()
classes, problems = load_classes()
fixes = []
if classes:
    p2, fixes = check_knowledge(classes)
    problems += p2 + check_vault_tags(classes)
for msg in problems:
    print("  ! " + msg)
for path, text, what in fixes:
    write(path, text, what)
if not problems and not fixes:
    print(f"  = {len(classes)} classes, all consistent")

if not APPLY:
    print("(check only — run with 'apply' to make these changes)")
