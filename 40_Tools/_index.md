---
title: 40_Tools 인덱스
created: 2026-10-16
updated: 2026-10-16
tags: [meta, agent/claude-1b219bef-b3db-4ef6-8088-81f7f0d19120]
source: ai
---

# 40_Tools 인덱스

> 볼트 밖에서 도는 도구(대시보드, 로컬 서버, CLI 등)의 도메인 (git 추적). 도구 하나가 독립 공개 저장소 하나이며 `<tool>/` 에 서브모듈로 들어온다.

상위: [[_Home]]

## 규칙

- [[도구 저장소 규칙]] — 담는 것과 담지 않는 것, 저장소 구성, 공개 면, README, Obsidian 노출

## 목록

> 서브모듈마다 한 줄 — `[[40_Tools/<tool>/README|<tool>]]` — 용도 · 저장소 · 기동. 서브모듈을 받지 않고 clone 한 환경에서는 링크 대상이 비어 있다.

- [[40_Tools/agent-dashboard/README|agent-dashboard]] — Claude·Codex 세션, Orca Run, `aplan` 계획을 실시간으로 보여 주는 로컬 웹 대시보드 · `s12171934/agent-dashboard` · `launchd/install.sh` (`DASH_LABEL`·`DASH_HOSTS`·`DASH_PYTHON`)
