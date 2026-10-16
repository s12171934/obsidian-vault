---
title: 20_Agents 인덱스
created: 2026-10-16
updated: 2026-10-16
tags: [meta, agent/claude-1b219bef-b3db-4ef6-8088-81f7f0d19120]
source: ai
---

# 20_Agents 인덱스

> 에이전트의 행동을 정의하는 도메인 (git 추적). `skills/` 는 이 기계에서 쓰는 스킬 목록의 원본이다.

상위: [[_Home]]

## 규칙

- [[20_Agents 범위 규칙]] — 이 도메인에 담는 것과 담지 않는 것
- [[스킬 로컬 연결 규칙]] — 도구 스킬 디렉터리를 `skills/` 로 연결하는 방식, `skills/` 폴더 규칙
- [[스킬 출처 관리 규칙]] — 내 스킬(서브모듈)·외부 스킬(`npx skills`)·로컬 전용 스킬의 형태와 git 처리
- [[스킬 저장소 규칙]] — 내 스킬 저장소의 단독 완결, 의존 수단, 공개 면, README

## 목록

> 내 스킬(서브모듈)만 한 줄씩 — `[[20_Agents/skills/<skill>/README|<skill>]]` — 용도 · 저장소. 서브모듈을 받지 않고 clone 한 환경에서는 링크 대상이 비어 있다. 외부 스킬 목록은 설치 도구의 기록 파일이 원본이다.

- [[20_Agents/skills/vault-entry/README|vault-entry]] — 볼트 밖 세션이 볼트 루트를 찾아 볼트 규칙 문서로 진입 · `s12171934/vault-entry`
- [[20_Agents/skills/vault-write-boundary/README|vault-write-boundary]] — 볼트 세션의 쓰기를 볼트 내부로 한정하는 경계 규칙 · `s12171934/vault-write-boundary`
- [[20_Agents/skills/implementation-approach/README|implementation-approach]] — 구현 작업의 오케스트레이션 방식 선택 (카탈로그·방식 문서 포함) · `s12171934/implementation-approach`
- [[20_Agents/skills/orca-work-placement/README|orca-work-placement]] — Orca 워크트리 배치와 에이전트 탭 명명·모델·목표 확정 · `s12171934/orca-work-placement`
- [[20_Agents/skills/orca-orchestration-rules/README|orca-orchestration-rules]] — Orca 감독형 오케스트레이션 진입 조건과 코디네이터 의무 · `s12171934/orca-orchestration-rules`
- [[20_Agents/skills/claude-usage-check/README|claude-usage-check]] — Claude 구독 사용량·초과 크레딧 실측 조회와 해석 · `s12171934/claude-usage-check`
- [[20_Agents/skills/aside-record/README|aside-record]] — Aside 에이전트 실행 화면 녹화와 타임라인 노트 · `s12171934/aside-record`
