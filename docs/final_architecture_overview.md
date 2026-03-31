# 🏗️ LLM Gateway — 코드 기준 시스템 아키텍처 가이드

이 문서는 `llm-gateway` 저장소의 **현재 실제 소스코드**를 기준으로 시스템 아키텍처, 데이터 플로우, 폴더 구조를 정리한 문서입니다.

기존의 추상적인 목표 구조가 아니라, 지금 저장소에 존재하는 파일과 실제 호출 경로를 기준으로 정리했습니다.

---

## 1. 시스템 아키텍처 (System Architecture)

### 1.1 전체 구조도

```mermaid
flowchart TB
    subgraph Frontend["Frontend / Control Plane"]
        Client["Client Application<br/>HTTP/JSON caller"]
        Dashboard["dashboard/app.py<br/>Streamlit dashboard<br/>httpx + pandas"]
        Metrics["dashboard/metrics.py<br/>Plotly chart helpers"]
    end

    subgraph App["Application Layer / FastAPI Data Plane"]
        Main["main.py<br/>FastAPI app<br/>Routes: /health, /v1/chat, /v1/orchestrate"]
        Auth["auth.py<br/>verify_api_key()<br/>FastAPI Depends"]
        Rate["rate_limit.py<br/>redis-py rate limiter"]
        Cache["cache.py<br/>SHA-256 payload cache"]
        Proxy["proxy.py<br/>httpx AsyncClient<br/>forward_to_llm()"]
        Policy["policy.py<br/>evaluate_policy()"]
        Registry["registry.py<br/>/admin/models CRUD"]
        Stats["stats.py<br/>/admin/stats analytics"]
        Logger["logger.py<br/>BackgroundTasks -> RequestLog"]
        Orchestrator["orchestrator.py<br/>decompose_task()<br/>estimate_resource_usage()"]
        Offloader["offloader.py<br/>select_optimal_node()<br/>run_orchestrated_offloading()"]
    end

    subgraph State["State & Persistence Layer"]
        DB["database.py<br/>SQLAlchemy async engine<br/>AsyncSessionLocal / get_db()"]
        Models["models.py<br/>Tenant / ApiKey / RequestLog / LLMModel"]
        Redis[("Redis<br/>rate limit + response cache")]
        Postgres[("PostgreSQL<br/>tenant, API key, model registry, request log")]
        Compose["docker-compose.yml<br/>redis:alpine<br/>postgres:16-alpine"]
    end

    subgraph External["External Target Layer"]
        Provider["Registered endpoint_url<br/>OpenAI / Anthropic / Ollama / custom endpoint"]
        Fallback["httpbin fallback<br/>demo path in proxy.py"]
    end

    Client --> Main
    Dashboard --> Stats
    Dashboard --> Main
    Metrics --> Dashboard

    Main --> Auth
    Auth --> DB
    Auth --> Models
    Auth --> Rate
    Rate --> Redis

    Main --> Cache
    Cache --> Redis

    Main --> Proxy
    Proxy --> Policy
    Proxy --> DB
    Proxy --> Models
    Proxy --> Provider
    Proxy -.->|fallback| Fallback

    Main -.->|BackgroundTasks| Logger
    Logger --> DB
    Logger --> Models

    Main --> Registry
    Registry --> DB
    Registry --> Models

    Main --> Stats
    Stats --> DB
    Stats --> Models

    Main --> Orchestrator
    Main --> Offloader
    Offloader --> Models
    Offloader --> Orchestrator

    DB --> Postgres
    Compose -.->|provisions| Redis
    Compose -.->|provisions| Postgres
```

### 1.2 스택과 소스코드 매핑

| 영역 | 사용 스택 | 실제 소스코드 |
|---|---|---|
| API 서버 | FastAPI, Uvicorn, Pydantic | `main.py`, `auth.py`, `registry.py`, `stats.py` |
| 외부 호출 | `httpx.AsyncClient` | `proxy.py` |
| 인증/인가 | FastAPI Depends, API Key 검증 | `auth.py` |
| 레이트 리밋 | Redis, `redis-py` | `rate_limit.py` |
| 응답 캐시 | Redis, SHA-256 payload hash | `cache.py` |
| 정책 라우팅 | Python rule engine | `policy.py`, `proxy.py` |
| 비동기 로깅 | FastAPI `BackgroundTasks` | `main.py`, `logger.py` |
| ORM / DB 액세스 | SQLAlchemy async, `asyncpg` | `database.py`, `models.py` |
| 모델 레지스트리 | REST admin API + PostgreSQL | `registry.py`, `models.py` |
| 통계 API | SQL aggregation + REST | `stats.py` |
| 오프로딩 시뮬레이션 | Pydantic models, resource estimation logic | `orchestrator.py`, `offloader.py` |
| 운영 대시보드 | Streamlit, pandas, Plotly, httpx | `dashboard/app.py`, `dashboard/metrics.py` |
| 인프라 실행 | Docker Compose, Redis, PostgreSQL | `docker-compose.yml` |

### 1.3 코드 기준 모듈 책임

| 모듈 | 역할 |
|---|---|
| `main.py` | FastAPI 앱 생성, 라우터 연결, `/v1/chat`, `/v1/orchestrate` 엔드포인트 제공 |
| `auth.py` | API Key를 DB에서 조회하고 팀 이름을 반환 |
| `rate_limit.py` | API Key 기준 분당 호출 횟수 제한 |
| `cache.py` | 요청 payload를 해시해서 Redis 캐시 조회/저장 |
| `proxy.py` | 정책 기반 모델 선택 후 외부 LLM endpoint로 요청 전달 |
| `policy.py` | `cost_optimal`, `quality_first`, `speed_optimal` 규칙 평가 |
| `logger.py` | 요청 결과를 `RequestLog` 테이블에 비동기 저장 |
| `database.py` | async engine / session factory / FastAPI dependency 제공 |
| `models.py` | 멀티테넌시, API Key, 로그, 모델 레지스트리 ORM 스키마 정의 |
| `registry.py` | 모델 목록 조회, 등록, 상태 변경 관리자 API |
| `stats.py` | 요약, 최근 로그, 모델 사용량, 비용 통계 API |
| `orchestrator.py` | 프롬프트를 하위 태스크로 분해하고 VRAM 사용량 추정 |
| `offloader.py` | 가용 모델 중 최적 노드 선택 및 오프로딩 계획 생성 |
| `dashboard/app.py` | 통계 API 호출 및 오프로딩 데모 UI |
| `dashboard/metrics.py` | 비용 추이, 모델 비중, 지연시간 분포 차트 렌더링 |

### 1.4 전체 워크플로우 한눈에 보기

```mermaid
flowchart LR
    Client["API Client"]
    Dashboard["Streamlit Dashboard"]
    Response["JSON Response"]
    Plan["Offloading Plan Response"]

    subgraph Gateway["FastAPI Gateway"]
        Chat["/v1/chat"]
        AdminAPI["/admin/stats<br/>/admin/models"]
        OrchAPI["/v1/orchestrate"]
        Auth["auth.py<br/>API key check"]
        Rate["rate_limit.py<br/>per-key limiter"]
        Cache["cache.py<br/>response cache"]
        Route["proxy.py + policy.py<br/>model selection and forwarding"]
        Decompose["orchestrator.py<br/>task decomposition"]
        Place["offloader.py<br/>node selection"]
        Log["logger.py<br/>background logging"]
    end

    Redis[("Redis")]
    Postgres[("PostgreSQL")]
    Provider["Registered LLM Endpoint"]
    Fallback["httpbin Fallback"]

    Client --> Chat
    Chat --> Auth
    Auth --> Postgres
    Auth --> Rate
    Rate --> Redis

    Chat --> Cache
    Cache --> Redis
    Cache -->|cache hit| Response
    Cache -->|cache miss| Route

    Route --> Postgres
    Route --> Provider
    Route -.->|error fallback| Fallback
    Route -.->|async log| Log
    Log --> Postgres
    Route --> Response

    Dashboard --> AdminAPI
    AdminAPI --> Postgres

    Dashboard --> OrchAPI
    OrchAPI --> Decompose
    Decompose --> Place
    Place --> Postgres
    Place --> Plan
```

---

## 2. 데이터 플로우 (Data Flow)

### 2.1 `/v1/chat` 요청 처리 시퀀스

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant API as main.py<br/>secure_chat()
    participant Auth as auth.py<br/>verify_api_key()
    participant Redis as Redis<br/>rate_limit + cache
    participant Proxy as proxy.py<br/>forward_to_llm()
    participant DB as PostgreSQL<br/>Tenant / ApiKey / LLMModel / RequestLog
    participant LLM as target endpoint<br/>or httpbin fallback
    participant Log as logger.py<br/>save_log_data()

    C->>API: POST /v1/chat + x-api-key + payload
    API->>Auth: FastAPI Depends
    Auth->>DB: ApiKey + Tenant 조회
    Auth->>Redis: INCR rate_limit:{api_key}
    Auth->>Redis: EXPIRE 60s (first hit)
    Auth-->>API: tenant_name

    API->>Redis: get_cache_key(payload)
    API->>Redis: GET llm_cache:{sha256(payload)}

    alt Cache Hit
        Redis-->>API: cached response
        API-->>C: {"proxy_success": true, "cached": true, ...}
        API-.->Log: BackgroundTasks.add_task(...)
        Log->>DB: INSERT RequestLog
    else Cache Miss
        Redis-->>API: None
        API->>Proxy: forward_to_llm(payload, tenant_name)
        Proxy->>DB: tenant routing_policy 조회
        Proxy->>DB: active LLMModel 목록 조회
        Proxy->>LLM: POST target_model.endpoint_url

        alt Upstream Success
            LLM-->>Proxy: JSON response + usage
        else Timeout / HTTPError
            Proxy->>LLM: POST https://httpbin.org/post
            LLM-->>Proxy: fallback JSON
        end

        Proxy-->>API: llm_result
        API->>Redis: SETEX llm_cache:{sha256(payload)}
        API-->>C: {"proxy_success": true, "cached": false, ...}
        API-.->Log: BackgroundTasks.add_task(...)
        Log->>DB: INSERT RequestLog
    end
```

### 2.2 `/v1/orchestrate` 오프로딩 시퀀스

```mermaid
sequenceDiagram
    autonumber
    participant U as Dashboard / Client
    participant API as main.py<br/>multi_agent_orchestrate()
    participant Orch as orchestrator.py<br/>decompose_task()
    participant DB as PostgreSQL<br/>LLMModel(status='prod')
    participant NodeSel as offloader.py<br/>run_orchestrated_offloading()

    U->>API: POST /v1/orchestrate {prompt}
    API->>Orch: decompose_task(prompt)
    Orch-->>API: OrchestratedRequest(sub_tasks)
    API->>DB: SELECT LLMModel WHERE status='prod'
    DB-->>API: available_models
    API->>NodeSel: run_orchestrated_offloading(orchestrated_req, available_models)

    loop each sub task
        NodeSel->>Orch: estimate_resource_usage(task, model.name)
        NodeSel->>NodeSel: compare vram_available_gb
        NodeSel->>NodeSel: choose best-fit model
    end

    NodeSel-->>API: offloading_plan
    API-->>U: original_prompt + task_count + offloading_plan
```

### 2.3 운영 대시보드 데이터 조회 흐름

```mermaid
sequenceDiagram
    autonumber
    participant Browser as Streamlit UI
    participant Dash as dashboard/app.py
    participant Stats as stats.py
    participant DB as PostgreSQL
    participant Charts as dashboard/metrics.py

    Browser->>Dash: 페이지 로드
    Dash->>Stats: GET /admin/stats/summary
    Dash->>Stats: GET /admin/stats/logs/recent
    Stats->>DB: aggregate / recent logs query
    DB-->>Stats: rows
    Stats-->>Dash: JSON payload
    Dash->>Charts: draw_cost_trend(df)
    Dash->>Charts: draw_model_usage(df)
    Dash->>Charts: draw_latency_dist(df)
    Charts-->>Browser: Plotly charts
```

---

## 3. 폴더 구조 (Folder Structure)

### 3.1 구조도

```mermaid
flowchart TB
    Root["llm-gateway/"]

    subgraph RootFiles["Root Python Modules"]
        RootHub["root modules/"]
        MainFile["main.py<br/>FastAPI entrypoint"]
        AuthFile["auth.py<br/>auth dependency"]
        ProxyFile["proxy.py<br/>LLM forwarding"]
        RateFile["rate_limit.py<br/>Redis limiter"]
        CacheFile["cache.py<br/>response cache"]
        LoggerFile["logger.py<br/>DB logger"]
        DBFile["database.py<br/>async DB setup"]
        ModelsFile["models.py<br/>ORM schema"]
        RegistryFile["registry.py<br/>model admin API"]
        StatsFile["stats.py<br/>analytics API"]
        PolicyFile["policy.py<br/>routing rules"]
        OrchFile["orchestrator.py<br/>task decomposition"]
        OffloaderFile["offloader.py<br/>resource-based placement"]
        ComposeFile["docker-compose.yml<br/>infra definition"]
    end

    subgraph DashboardDir["dashboard/"]
        DashboardHub["dashboard/"]
        DashApp["app.py<br/>Streamlit app"]
        DashMetrics["metrics.py<br/>Plotly chart helpers"]
    end

    subgraph DocsDir["docs/"]
        DocsHub["docs/"]
        FinalDoc["final_architecture_overview.md"]
        ArchDoc["architecture.md"]
        EntDoc["enterprise_overview.md"]
        PhaseDoc["phase_analysis_report.md"]
        Roadmap["roadmap.md"]
        Steps["step1.md ~ step5.md"]
        DrawScripts["draw_arch.py / draw_arch2.py<br/>draw_ent_arch.py / draw_workflow.py"]
        Images["architecture_img.png<br/>ent_architecture_img.png<br/>ent_workflow_img.png"]
    end

    subgraph RuntimeDir["Local Runtime Artifacts"]
        RuntimeHub["runtime artifacts/"]
        Venv["venv/<br/>project-local virtualenv"]
        GitDir[".git/<br/>Git metadata"]
        PyCache["__pycache__/<br/>compiled Python cache"]
    end

    Root --> RootHub
    Root --> DashboardHub
    Root --> DocsHub
    Root --> RuntimeHub

    RootHub --> MainFile
    RootHub --> AuthFile
    RootHub --> ProxyFile
    RootHub --> RateFile
    RootHub --> CacheFile
    RootHub --> LoggerFile
    RootHub --> DBFile
    RootHub --> ModelsFile
    RootHub --> RegistryFile
    RootHub --> StatsFile
    RootHub --> PolicyFile
    RootHub --> OrchFile
    RootHub --> OffloaderFile
    RootHub --> ComposeFile

    DashboardHub --> DashApp
    DashboardHub --> DashMetrics

    DocsHub --> FinalDoc
    DocsHub --> ArchDoc
    DocsHub --> EntDoc
    DocsHub --> PhaseDoc
    DocsHub --> Roadmap
    DocsHub --> Steps
    DocsHub --> DrawScripts
    DocsHub --> Images

    RuntimeHub --> Venv
    RuntimeHub --> GitDir
    RuntimeHub --> PyCache
```

### 3.2 실제 트리 스냅샷

```text
llm-gateway/
├── auth.py
├── cache.py
├── database.py
├── docker-compose.yml
├── logger.py
├── main.py
├── models.py
├── offloader.py
├── orchestrator.py
├── policy.py
├── proxy.py
├── rate_limit.py
├── registry.py
├── stats.py
├── dashboard/
│   ├── app.py
│   └── metrics.py
├── docs/
│   ├── architecture.md
│   ├── draw_arch.py
│   ├── draw_arch2.py
│   ├── draw_ent_arch.py
│   ├── draw_workflow.py
│   ├── enterprise_overview.md
│   ├── final_architecture_overview.md
│   ├── phase_analysis_report.md
│   ├── roadmap.md
│   ├── step1.md
│   ├── step2.md
│   ├── step3.md
│   ├── step4.md
│   └── step5.md
├── venv/
├── .git/
└── __pycache__/
```

---

## 4. 문서 해석 가이드

- 이 문서는 `2026-04-01` 시점의 실제 저장소를 기준으로 작성했습니다.
- `memory_router.py`, `requirements.txt`, `dashboard/pages/` 같은 항목은 현재 저장소에는 없어서 구조도에 넣지 않았습니다.
- `/admin/models`, `/admin/stats`는 현재 코드상 별도 관리자 인증 없이 `main.py`에 연결되어 있습니다.
- `proxy.py`의 외부 호출 대상은 `LLMModel.endpoint_url`이며, 실패 시 `httpbin` fallback 경로가 존재합니다.
- 오프로딩 경로는 `orchestrator.py` + `offloader.py` 기반의 시뮬레이션 로직입니다.
