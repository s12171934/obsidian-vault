---
title: 40_Tools 인덱스
created: 2026-10-16
updated: 2026-11-12
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
- [[40_Tools/checkbox-driver/README|checkbox-driver]] — 「티켓 체크박스 커밋 리뷰」 방식을 LLM 없이 모는 스크립트 드라이버(스케줄러·티켓 드라이버) · `s12171934/checkbox-driver` · `bin/cbd <키> schedule`
- [[40_Tools/header-injector/README|header-injector]] — 장애 주입 헤더를 개발자도구 패널에서 여러 규칙으로 켜고 끄는 Chrome 확장 · 로컬 전용(사내 값 내장, push 금지, 서브모듈 미등록) · 저장소 폴더를 Chrome 에 로드
- [[40_Tools/widget-studio/README|widget-studio]] — 문구·시계·D-day·사진 템플릿으로 아이폰 홈 화면 위젯을 디자인하는 iOS 앱(SwiftUI·WidgetKit) · `s12171934/widget-studio` · `bin/widget-studio run`
- [[40_Tools/workflow-canvas/README|workflow-canvas]] — Orca CLI의 Run·Task를 그래프로 가져와 워크플로 편집과 단계별 실행 상태를 보여 주는 로컬 웹뷰 · `s12171934/workflow-canvas` · `bin/workflow-canvas`
