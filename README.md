# 미국 원전 사업전략 백데이터 에이전트

삼성물산 원전영업팀의 **미국 대형원전 & SMR 사업전략**을 뒷받침하는 백데이터 구축 도구.
**유틸리티 · 주(State) · 사업기회(Opportunity)** 3축으로 공개 자료를 수집·정규화하고,
**EPC 수주(1순위) / 지분투자(2순위)** 관점으로 사업기회를 전략 점수화해 대시보드로 시각화한다.

> 대미투자 맥락: 2026.9.30 **미-한 원전 프레임워크**(AP1000 6기 + APR1400 2기, $120B,
> 한국기업 EPC 우선참여)가 전략의 중심축이다. 지분투자는 EPC·시공 사업권 확보 수단으로 본다.

로컬에 Python을 설치할 필요가 없다. **GitHub Actions**(클라우드 러너)가 신호를 수집·점수화하고,
**GitHub Pages**가 대시보드를 호스팅한다.

---

## 구조

```
us-nuclear-strategy-agent/
├─ data/
│  ├─ strategy_rubric.json    # 전략 평가 루브릭 (6차원 · EPC 우선 가중)
│  ├─ utilities.json          # 유틸리티(사업자) DB — 선단·시장·전략신호·EPC우선순위
│  ├─ states.json             # 주 DB — 전력시장 구조·원전용량·정책·EPC매력도
│  └─ opportunities.json      # 사업기회 DB — 6차원 점수 + sales_note(삼성물산 관점)
├─ src/
│  ├─ scoring.py              # 전략 점수 엔진 (level 1~5 → 가중 0~100, EPC 우선)
│  ├─ collect.py              # 공개 신호 수집 오케스트레이터 (덮어쓰지 않음·검토 플래그)
│  ├─ build_dashboard.py      # 점수 + 3축 + 신호 → dashboard/data.js
│  └─ sources/                # 공개기관 커넥터 계층
│     ├─ base.py              #   커넥터 공통 인터페이스
│     ├─ registry.py          #   참조 소스 목록(EIA·NRC·DOE·프레임워크…)
│     ├─ eia.py               #   EIA v2 — 주별 원자력 발전량(무료 API 키)
│     ├─ nrc.py               #   NRC — 인허가 상태(참조 계층)
│     ├─ googlenews.py        #   유틸리티·사업기회 최신 신호(FID·건설허가·EPC·offtake)
│     └─ wikipedia.py         #   유틸리티·플랜트 개요
├─ dashboard/
│  └─ index.html             # 대시보드 (3축 뷰 · data.js 있으면 우선, 없으면 베이스라인)
├─ .github/workflows/deploy.yml   # 수집→빌드→Pages 배포 (주간 자동)
└─ requirements.txt
```

### 데이터 흐름

1. `src/sources/*` 커넥터가 공개 소스에서 신호를 수집 → `collect.py`가 `data/collected.json`·`collection_report.md` 생성
2. `scoring.py`가 `strategy_rubric.json` 가중치(EPC 우선)로 사업기회별 종합점수 산출
3. `build_dashboard.py`가 점수 + 유틸리티 + 주 + 라이브 신호를 `dashboard/data.js`로 내보냄
4. `dashboard/index.html`이 이를 읽어 랭킹·3축 테이블로 표시
   (`data.js`가 없으면 HTML 내장 베이스라인/`data/*.json` fetch로 동작)

---

## 3축 분석 단위

| 축 | 파일 | 핵심 질문 |
|---|---|---|
| **유틸리티(사업자)** | `utilities.json` | 누가 발주하는가? 선단·시장노출·전략신호·삼성 EPC 우선순위 |
| **주(State)** | `states.json` | 어디가 유리한가? 규제/탈규제 시장구조·정책·데이터센터 수요·EPC 매력도 |
| **사업기회(Opportunity)** | `opportunities.json` | 무엇을 수주하는가? 신규대형·재가동·SMR 건별 6차원 점수 + 시사점 |

세 축은 `utility_id`·주 코드·`reactor_nohyeong_id`로 상호 연결된다.

---

## 전략 평가 차원 (strategy_rubric v0.1 — EPC 우선 가중)

| 차원 | 가중 | 설명 |
|---|---|---|
| **EPC 수주 접근성** | 28% | EPC가 경쟁입찰로 열렸는가 vs 자체수행·기지정 |
| **발주 확실성** | 22% | FID·건설허가·offtake 확보로 실제 발주될 확률 |
| **한국기업 레버리지** | 20% | 미-한 프레임워크·$350B 패키지 연계 우선참여 |
| **사업 규모** | 12% | capex·용량·후속호기 파이프라인 |
| **재무·정책 지원** | 10% | DOE 대출·rate-base·데이터센터 offtake |
| **수행 리스크(역)** | 8% | FOAK·HALEU·인허가 리스크(낮을수록 고점) |

성숙도/매력도 1~5 × 가중합 → 0~100. **데이터 신뢰도**(高/中/低)를 함께 기록·보정한다.

---

## 핵심 사업기회 (2026.10 베이스라인 · 점수 상위)

- **미-한 프레임워크 AP1000 6기** — Phase1 2기 EPC 계약이 진입 관문 (★ 최우선)
- **미-한 프레임워크 APR1400 2기** — 한국 노형, 팀코리아 EPC 주도 (★ 최우선)
- **TVA Clinch River BWRX-300** — 건설허가 취득(2026.9)·최대 4기, 가장 확실한 SMR 신규
- **Duke Carolinas / Dominion North Anna / V.C. Summer 완공** — 규제시장·데이터센터 수요 연계 대형·SMR
- **재가동**(Palisades·Crane·Duane Arnold) — 트렌드 지표, 직접 EPC 여지는 제한적

> 상세 수치·시사점은 대시보드(① 사업기회 랭킹) 참조.

---

## 참조 공개 데이터 소스

| 소스 | 제공 | 라이브 |
|---|---|---|
| U.S. EIA (v2 API) | 주별 원자력 용량·발전량 | ○ (무료 키) |
| U.S. NRC | 인허가 상태·운영로 목록 | 참조 |
| IAEA PRIS | 미국 원자로 상태 | 참조 |
| U.S. DOE / LPO | 대출·ARDP·금융지원 | 참조 |
| Google News (RSS) | FID·건설허가·EPC·offtake 신호 | ○ |
| Wikipedia REST | 유틸리티·플랜트 개요 | ○ |
| WNA / World Nuclear News | 동향 서술 | 참조 |
| 미-한 프레임워크 (MOTIE/US DOC) | AP1000·APR1400 구성·한국참여 원칙 | 참조 |

> 라이브 커넥터는 상태 변화를 **제안**하고, 큐레이션 값과 불일치 시 `검토 필요`로 플래그한다.
> **큐레이션된 전략평가(level/confidence)는 덮어쓰지 않는다** — 수집·제시는 에이전트, 수주 판단은 사람.

---

## GitHub로 배포하기 (로컬 Python 불필요)

1. 이 폴더를 GitHub 저장소(`moojungra/US-nuclear-strategy`)로 push
2. 저장소 **Settings → Pages → Build and deployment → Source: GitHub Actions** 선택
3. `main`에 push하면 Actions가 자동으로 데이터 생성 + Pages 배포
4. 배포 URL: `https://moojungra.github.io/US-nuclear-strategy/`
5. 매주 월요일 자동 재빌드(또는 Actions 탭에서 수동 실행)
6. (선택) EIA 교차검증: 저장소 **Settings → Secrets → Actions**에 `EIA_API_KEY` 등록
   (무료 발급: https://www.eia.gov/opendata/ ). 없어도 나머지는 정상 동작.

### 로컬에서 돌려보려면 (선택, Python 필요)

```bash
pip install -r requirements.txt
python src/scoring.py            # 콘솔 전략 랭킹 출력
python src/collect.py            # 라이브 신호 수집(선택)
python src/build_dashboard.py    # dashboard/data.js 생성
```

---

## 주의

공개 자료 기반 **베이스라인**이며 수치·시점은 근사·변동 가능하다. 각 항목의 confidence와
sources를 함께 확인할 것. 의사결정 보조용이며 1차 자료 검증을 대체하지 않는다.
`sales_note`는 삼성물산 EPC수주·지분투자 관점의 해석이며, 실제 수주전략은 내부 검토로 확정한다.

자매 프로젝트: 노형 기술평가 `smr-evaluation-agent`, 일일 동향 `nuclear-news-agent`.
