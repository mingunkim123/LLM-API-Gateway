# LLM API Gateway 시스템 아키텍처 및 데이터 흐름도

본 문서는 LLM API Gateway 프로젝트의 전체 시스템 구조와 클라이언트 요청이 처리되는 라이프사이클을 설명합니다.

## 1. 시스템 전체 아키텍처 (System Architecture)

![LLM API Gateway Architecture](/home/mingun/AI_Flatform/llm-gateway/docs/architecture_img.png)

(위 아키텍처 이미지는 `docs/draw_arch.py` 파이썬 스크립트를 통해 생성되었습니다.)

## 2. 프로젝트 전체 흐름 (Project Lifecycle Flow)

이 시스템은 클라이언트와 실제 대형 언어 모델(LLM) 사이의 미들웨어(Middleware)로 동작합니다. 핵심 로직의 흐름은 다음과 같습니다.

### 단계 1: 요청 접수 및 인증 (Authentication)
* 클라이언트는 발급받은 `API Key`를 HTTP 헤더(예: `Authorization: Bearer <Key>`)에 담아 게이트웨이에 요청합니다.
* FastAPI는 의존성 주입(Dependency Injection)을 통한 공통 미들웨어에서 API Key를 가로채고, 데이터베이스(PostgreSQL)에서 유효한 사용자와 키인지 검증합니다. (이 과정의 성능을 높이기 위해 인증 결과도 일시적으로 Redis에 캐싱할 수 있습니다.)

### 단계 2: 트래픽 제어 (Rate Limiting)
* 인증된 클라이언트라 할지라도 무제한으로 API를 호출하게 두면 과도한 과금 폭탄을 맞을 수 있습니다.
* Redis에 클라이언트 식별자(API Key ID 등)를 키로 사용하여 타임 윈도우(예: 1분당 최대 50회) 기반의 호출 횟수를 카운트합니다. 초과 시 `429 Too Many Requests` 상태 코드를 즉시 반환하며 LLM으로 요청을 라우팅하지 않습니다.

### 단계 3: 프록시 전달 (Reverse Proxying)
* 요청 유효성이 모두 확인되면, 클라이언트가 의도한 엔드포인트(OpenAI, Anthropic 등) 형식을 그대로 맞추어 비동기 HTTP 클라이언트(예: `httpx`)를 통해 요청을 전달합니다. (이를 리버스 프록시 패턴이라고 합니다.)

### 단계 4: 캐싱 및 응답 반환 (Response & Caching)
* 매우 유사하거나 완전히 동일한 프롬프트 요청에 대해서는 이전의 응답 결과를 Redis 캐시에 일정 시간 저장해두고, 이를 바로 반환하여 모델 호출 비용과 지연 시간(Latency)을 절약하게 설계할 수 있습니다. 
* 외부 모델 API로부터 응답을 받으면 지체 없이 서버를 거쳐 클라이언트에게 결과값을 반환합니다.

### 단계 5: 비동기 로깅 (Background Logging)
* 응답은 빠른 속도로 클라이언트에게 전송되어야 하므로, 이 과정 이후에 **PostgreSQL 로깅** 작업을 수행합니다.
* FastAPI의 `Background Tasks`를 이용해 어떤 사용자가 어떤 모델을 호출했는지, 프롬프트 내용, 응답 크기, 응답까지 몇 ms가 걸렸는지 등을 `RequestLog` 테이블에 비동기로 안전하게 Insert 합니다. 이를 통해 모델별 통계 대시보드 및 사용자별 과금 증빙 자료를 생성할 수 있습니다.
