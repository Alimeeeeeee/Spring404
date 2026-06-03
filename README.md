<div align="center">

# 여기지!  
### 여성 1인 여행자를 위해, AI 기반 안전 분석으로 정보 공백을 해결하고 안전 경로를 추천하는 지도 서비스

데이터 기반 안전 정보, 지도 시각화, 경로 추천을 통해  
여성 1인 여행자의 이동 불안과 정보 공백을 줄이는 안전 여행 지원 웹 서비스

<br />

**Team 404** · 이아림 · 노유나 · 이채원  
산학 프로젝트

</div>

---

## Overview

여기지!는 사용자 리뷰와 공공데이터를 기반으로 위치별 안전도를 산출하고,  
이를 지도 위에 시각화하여 더 안전한 이동 경로를 추천하는 서비스입니다.

기존 지도 서비스가 거리와 시간 중심의 경로 탐색에 집중한다면,  
여기지!는 사용자의 실제 이동 환경에서 중요한 기준이 될 수 있는 '안전성'에 주목합니다.

AI 분석을 통해 리뷰 데이터를 정량화하고, 이를 지역 안전 정보와 결합하여  
사용자가 보다 안전한 경로를 선택할 수 있도록 지원하는 것을 목표로 합니다.

---

## Problem

기존 지도 서비스는 주로 최단 거리와 소요 시간을 기준으로 경로를 제공합니다.  
하지만 낯선 지역이나 늦은 시간대의 이동에서는 경로의 안전성이 더 중요한 판단 기준이 될 수 있습니다.

특히 여성 1인 여행자의 경우, 신뢰할 수 있는 안전 정보가 부족하면  
이동 자체에 대한 심리적 부담이 커지고 선택 가능한 동선도 제한될 수 있습니다.

저희는 이러한 정보 공백이 실제 이동의 제약으로 이어진다고 보았고,  
안전도를 반영한 지도 시각화와 경로 추천이 필요하다고 판단했습니다.

---

## Solution

본 프로젝트는 아래 3가지 핵심 기능으로 문제를 해결합니다.

### 1. 안전 데이터 기반 지도 시각화
- 사용자 리뷰 중심 기반 안전 점수 DB 구축
- Google Maps 기반 안전도 시각화

### 2. AI 기반 안전 여행 경로 추천
- OpenAI API를 활용한 안전 경로 생성
- 안전도 + 위치 반영

---

## MVP

본 프로젝트의 핵심 MVP는 데이터 기반 안전 지도 (Safety Map) 입니다.

### 핵심 기능 : 안전 지도 시각화 및 안전 경로 추천 시스템

- 사용자 리뷰 데이터 입력 (위험/안전 경험)  
- 공공 데이터(지역 범죄율, 거리 활성도 등) 연동 및 통합 
- 장소별 안전 점수 산출  
- 안전도 시각화 및 경로 추천

### 결과
- 사용자는 특정 지역의 안전도를 직관적으로 확인 가능  
- “어디가 안전한가?”를 지도에서 판단 가능  
- 출발지~목적지 간 더 안전한 이동 경로 선택 가능

### 핵심 가치
- 여성 1인 이동 시 발생하는 불안감 최소화  
- 안전 정보를 기반으로 한 자율적 이동권 강화  
- 단순 길찾기가 아닌 안전 중심 경로 선택 가능

---

## Core Logic

### 안전 지도 생성 로직 (Safety Map Generation)

본 시스템의 핵심 로직은 사용자 리뷰 데이터 + 공공 데이터 분석을 통한 안전도 점수 산출 및 지도 시각화입니다.

**1. 데이터 수집**  
사용자 리뷰 데이터 (위험/안전 경험, 텍스트 입력)  
공공 데이터 (치안 정보, 사고 발생률, 환경 데이터 등)

**2. 데이터 전처리**  
리뷰 텍스트 정제 (불용어 제거, 키워드 추출)  
지역 단위로 데이터 정렬 및 통합

**3. 안전도 점수 계산**  
사용자 리뷰 기반 점수  
공공 데이터 기반 위험도 점수

**4. 안전 지도 생성**  
Google Maps 기반 지도 렌더링  
지역별 safety_score를 평점으로 변환

---

## Architecture

```text
User
↓
Frontend (React + Google Maps)
↓
Backend (FastAPI)
↓
Database (MySQL)
↓
Backend (FastAPI)
↓
AI Engine (OpenAI API)
↓
Response
↓
User
```

---

## Tech Stack

| Layer | Stack |
|---|---|
| Frontend | React, JavaScript / HTML / CSS, Google Cloud Console |
| Backend | FastAPI, Python |
| Database | MySQL |
| Data Processing | CSV, Python Script |
| AI | OpenAI API |
| Deployment | Vercel, Render |
---

## Repository Structure

```text
📦 Project Root(Spring404)
┣ 📁 frontend
┃ ┗ 📁 src
┃   ┣ App.jsx
┃   ┣ AppViews.jsx
┃   ┣ mapHelpers.js
┃   ┣ styles.js
┃   ┗ main.jsx
┃ ┣ index.html
┃ ┣ package.json
┃ ┗ package-lock.json
┣ 📁 backend
┃ ┣ 📁 data
┃ ┃ ┣ police_hongdae_1km.csv
┃ ┃ ┣ public_facilities_hongdae_1km.csv
┃ ┃ ┗ sample_lamp.csv
┃ ┣ 📁 scripts
┃ ┃ ┣ geocode_addresses.py
┃ ┃ ┗ import_public_safety_csv.py
┃ ┣ .gitignore
┃ ┣ db.py
┃ ┣ main.py
┃ ┣ schemas.py
┃ ┗ requirements.txt
┣ 📁 ai
┃ ┣ .gitignore
┃ ┣ main.py
┃ ┣ ai_scoring.py
┃ ┗ requirements.txt
┃ 📁 doc
┃ ┣ PMF_analysis.md
┃ ┗ elevator_speech.md
┣ .gitignore
┣ render.yaml
┣ self_demo.md
┗ README.md
```

### Project Structure

#### frontend
`App.jsx`
- React 기반 메인 화면 구현
- Google Maps 기반 지도 기능 구현

`AppViews.jsx`
- 화면 구성 컴포넌트 관리
- 하단 패널 UI 구현

`mapHelpers.js`
- 지도 설정값 및 API 주소 관리
- 거리·시간 포맷 유틸리티 함수 제공

`styles.js`
- 공통 스타일 및 UI 스타일 관리

`main.jsx`
- React 실행 파일

`index.html`
- React 실행을 위한 기본 HTML 파일

`package.json`
- 프로젝트에 필요한 라이브러리 정보 관리
- 실행 및 빌드 스크립트 관리

`package-lock.json`
- 사용된 라이브러리 버전 정보 관리

#### backend

`.gitignore`
- 깃허브에 업로드하지 않을 파일 목록 관리
- venv, 캐시 파일, 환경변수 등 제외 설정

`db.py`
- MySQL 데이터베이스 연결 및 관리
- 안전 지도 격자 구역 생성
- 좌표 기반 `zone_id` 계산 로직 관리
- 리뷰 데이터 저장 및 조회 기능 구현
- 공공 안전 인프라 데이터 조회 및 집계 데이터 관리
- 리뷰 점수와 공공 안전 점수를 결합한 최종 안전 점수 계산

`main.py`
- FastAPI 기반 백엔드 서버 실행 파일
- API 엔드포인트 정의 및 요청 처리
- AI 서버와 통신하여 리뷰 위험도 분석 요청
- 리뷰 저장 및 조회 API 제공
- 지도 시각화를 위한 구역별 안전 점수 API 제공
- 경로 후보별 안전도 랭킹 API 제공
- 서버 상태 확인을 위한 헬스체크 API 제공

`schemas.py`
- 요청/응답 데이터 구조 정의
- 리뷰 생성 요청 데이터 검증 및 타입 관리
- 공공 안전 구역 데이터 검증 및 타입 관리
- 경로 안전도 평가 요청 데이터 검증 및 타입 관리

`requirements.txt`
- 백엔드 실행에 필요한 라이브러리 목록
- 동일한 개발 환경 재현을 위한 의존성 관리 파일

`data/`
- 공공 안전 인프라 CSV 데이터 관리
- CCTV, 편의점, 경찰 시설, 보안등 데이터 보관
- 공공 안전 점수 계산을 위한 초기 적재 데이터 관리

`scripts/`
- 공공 안전 인프라 CSV 데이터 전처리 및 적재 스크립트 관리
- 좌표 기반 시설 데이터를 격자 구역별 개수로 집계
- 주소 기반 데이터를 위도/경도 좌표로 변환하는 보조 도구 관리

#### ai
`.gitignore`
- 깃허브에 업로드하지 않을 파일 목록 관리

`main.py`
- FastAPI 기반 AI 분석 및 경로 랭킹 API 서버 메인 파일
- 실시간 리뷰 감성 분석 및 평균 안심 점수 알고리즘 수행

`ai_scoring.py`
- AI 서버 인스턴스 연동 및 보조 스크립트
- 메인 API 파이프라인의 수치 연산 및 구동 환경 지원

`requirements.txt`
- AI 서버 실행에 필요한 라이브러리 목록
- 서버 환경 구축을 위한 의존성 관리 파일


---

## Expected Impact

- 여성 1인 여행자의 심리적 안정성 증가
- 데이터 기반 위험 회피 가능
- 안전 중심 여행 환경 구축

---

## Closing

여기지!는 단순 여행 경로 서비스가 아니라  
**안전이라는 기준을 중심으로 여행을 돕는 서비스**입니다.
