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
Projects (10_Projects/<project>/ with 일정/ and stage folders `<no> <name>/`):
- step notes 일정/*.md are mapped to stages by file name (`<project key> <stage> …`), with status/date/endDate
  from front matter; `<project> 타임라인.md` gets its 「타임라인」 section rewritten as a step table, and
  progress.json is written in agent-dashboard's exports/project-progress.schema.json form (facts only).
Tags: type/ values must be registered and every note must carry exactly one agent/ tag with a registered prefix
(registries are read from 00_Vault/rules/노트 작성 규칙.md §3). Notes this script creates get the agent/ tag of
the session running it.
Problems are printed as `  ! …`; only the 50 tag rewrite is fixed automatically. Standard library only.
"""
import datetime
import json
import os
import re
import sys

LOCAL_DOMAINS = ["10_Projects", "30_Automations", "50_Knowledge"]
VAULT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
STRUCTURE = os.path.join(VAULT, "00_Vault", "rules", "폴더 구조 규칙.md")
TODAY = datetime.date.today().isoformat()
APPLY = len(sys.argv) > 1 and sys.argv[1] == "apply"
if os.environ.get("CLAUDE_CODE_SESSION_ID"):
    AGENT_TAG = "agent/claude-" + os.environ["CLAUDE_CODE_SESSION_ID"]
elif os.environ.get("CODEX_THREAD_ID"):
    AGENT_TAG = "agent/codex-" + os.environ["CODEX_THREAD_ID"]
else:
    AGENT_TAG = "agent/미상"
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
        text = (f"---\ntitle: {title}\ncreated: {TODAY}\nupdated: {TODAY}\ntags: [meta, {AGENT_TAG}]\nsource: ai\n---\n\n"
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
    write(log, (f"---\ntitle: CHANGE_LOG\ncreated: {TODAY}\nupdated: {TODAY}\ntags: [meta, {AGENT_TAG}]\nsource: ai\n---\n\n"
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
    text = (f"---\ntitle: 지식 분류표\ncreated: {TODAY}\nupdated: {TODAY}\ntags: [meta, {AGENT_TAG}]\nsource: ai\n---\n\n"
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

# ---- projects: timeline and progress.json ----
PROJECTS = os.path.join(VAULT, "10_Projects")
STEP_STATUS = ("scheduling", "pending", "active", "done", "failed")
SKIP_PROJECT_DIRS = {"rules", "규칙 템플릿"}


def project_progress(pdir, name):
    """Return (progress dict, timeline section, problems) for a project, or None if it has no stage layout."""
    stages = []
    for d in os.listdir(pdir):
        m = re.match(r"^(\d+) (.+)$", d)
        if m and os.path.isdir(os.path.join(pdir, d)):
            stages.append({"no": int(m.group(1)), "name": m.group(2), "steps": []})
    sched = os.path.join(pdir, "일정")
    if not stages or not os.path.isdir(sched):
        return None
    stages.sort(key=lambda s: s["no"])
    key, problems = name.split()[0], []
    by_len = sorted(stages, key=lambda s: -len(s["name"]))
    for f in sorted(os.listdir(sched)):
        if not f.endswith(".md"):
            continue
        rel = f"10_Projects/{name}/일정/{f}"
        stem = f[:-3]
        rest = stem[len(key) + 1:] if stem.startswith(key + " ") else None
        stage = next((s for s in by_len if rest is not None and (rest == s["name"] or rest.startswith(s["name"] + " "))), None)
        if stage is None:
            problems.append(f"step note not named `{key} <stage> …` for a stage folder: {rel}")
            continue
        fm = front(read(os.path.join(sched, f)))
        status = fm.get("status", "").strip()
        step = {"path": f"일정/{f}"}
        if status not in STEP_STATUS:
            problems.append(f"step status must be one of {'/'.join(STEP_STATUS)}: {rel}")
            continue
        for k in ("date", "endDate"):
            v = fm.get(k, "").strip()
            if v:
                if not re.fullmatch(r"\d{4}-\d\d-\d\d", v):
                    problems.append(f"{k} is not YYYY-MM-DD: {rel}")
                step[k] = v
        if status == "scheduling" and ("date" in step or "endDate" in step):
            problems.append(f"scheduling step must not have dates (left out of progress.json): {rel}")
            continue
        if status != "scheduling" and "date" not in step:
            problems.append(f"{status} step needs date (left out of progress.json): {rel}")
            continue
        step["status"] = status
        stage["steps"].append(step)
    for s in stages:
        s["steps"].sort(key=lambda x: (x.get("date", "9999"), x["path"]))
    progress = {"schemaVersion": 1, "project": name}
    rdir = os.path.join(pdir, "rules")
    if os.path.isdir(rdir):
        for f in sorted(os.listdir(rdir)):
            m = f.endswith(".md") and re.search(r"템플릿: (\S+) 템플릿", read(os.path.join(rdir, f)))
            if m:
                progress["template"] = m.group(1)
                break
    progress["stages"] = stages
    rows = [f"| {s['no']} {s['name']} | [[{os.path.basename(x['path'])[:-3]}]] | {x['status']} | "
            f"{x.get('date', '—')} | {x.get('endDate', '—')} |" for s in stages for x in s["steps"]]
    section = ("## 타임라인\n\n> `local_index.py` 가 `일정/` 의 스텝 노트로부터 다시 쓴다. 손으로 고치지 않는다.\n\n"
               "| 스테이지 | 스텝 | 상태 | 시작 | 종료 |\n| --- | --- | --- | --- | --- |\n" + "\n".join(rows) + "\n")
    return progress, section, problems


def build_projects():
    print("[10_Projects progress]")
    if not os.path.isdir(PROJECTS):
        return
    seen = False
    for name in sorted(os.listdir(PROJECTS)):
        pdir = os.path.join(PROJECTS, name)
        if name in SKIP_PROJECT_DIRS or name.startswith(".") or not os.path.isdir(pdir):
            continue
        res = project_progress(pdir, name)
        if res is None:
            continue
        seen = True
        progress, section, problems = res
        for msg in problems:
            print("  ! " + msg)
        jpath = os.path.join(pdir, "progress.json")
        jtext = json.dumps(progress, ensure_ascii=False, indent=2) + "\n"
        if not os.path.exists(jpath) or read(jpath) != jtext:
            write(jpath, jtext, f"write 10_Projects/{name}/progress.json")
        tpath = os.path.join(pdir, f"{name} 타임라인.md")
        if os.path.exists(tpath):
            old = read(tpath)
            m = re.search(r"^## 타임라인\n.*?(?=^## |\Z)", old, re.M | re.S)
            new = (old[:m.start()] + section + ("\n" if old[m.end():] else "") + old[m.end():]) if m \
                else old.rstrip("\n") + "\n\n" + section
            if new != old:
                new = re.sub(r"^updated: .*$", f"updated: {TODAY}", new, count=1, flags=re.M)
                write(tpath, new, f"rewrite 「타임라인」 in 10_Projects/{name}/{name} 타임라인.md")
        else:
            print(f"  ! no timeline note: 10_Projects/{name}/{name} 타임라인.md")
    if not seen:
        print("  = no project with 일정/ and stage folders")


# ---- tag registries: type/ and agent/ ----
def check_type_agent():
    rule = read(NOTE_RULE)
    m = re.search(r"작업 성격 \(`type/`\)\*\* — 등록된 값: (.+)$", rule, re.M)
    types = set(re.findall(r"`([^`/]+)`", m.group(1).split(".")[0])) if m else set()
    m = re.search(r"등록된 도구 접두사: (.+?)\. ", rule)
    prefixes = re.findall(r"`([a-z0-9-]+)`\(", m.group(1)) if m else []
    print("[type/ · agent/ tags]")
    missing, problems = [], []
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules"]
        for f in files:
            if not f.endswith(".md") or f in ("SKILL.md", "CLAUDE.md"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, VAULT)
            tm = re.search(r"^tags:\s*\[(.*)\]\s*$", read(path), re.M)
            if not tm:
                continue
            tags = [x.strip() for x in tm.group(1).split(",")]
            for x in tags:
                if x.startswith("type/") and x[5:] not in types and "<" not in x:
                    problems.append(f"unregistered {x}: {rel}")
            agents = [x for x in tags if x.startswith("agent/")]
            if not agents:
                missing.append(rel)
            elif len(agents) > 1:
                problems.append(f"more than one agent/ tag: {rel}")
            elif agents[0] != "agent/미상" and "<" not in agents[0] and \
                    not any(agents[0].startswith(f"agent/{p}-") and len(agents[0]) > len(p) + 7 for p in prefixes):
                problems.append(f"agent/ tag without a registered prefix: {rel}")
    for msg in problems:
        print("  ! " + msg)
    if missing:
        print(f"  ! {len(missing)} notes without an agent/ tag, e.g. " + "; ".join(missing[:3]))
    if not problems and not missing:
        print(f"  = {len(types)} type values, prefixes {', '.join(prefixes)}; all notes tagged")


build_projects()
check_type_agent()

if not APPLY:
    print("(check only — run with 'apply' to make these changes)")
