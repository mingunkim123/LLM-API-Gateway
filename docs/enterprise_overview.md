# Enterprise LLM API Gateway & MLOps Platform 설계서

본 문서는 엔터프라이즈 AI 플랫폼으로 기능이 대폭 확장된 **전체 아키텍처**와 모델 평가/배포를 위한 **생애주기 워크플로우**를 정의한 문서입니다.

## 1. 플랫폼 전체 아키텍처 (Platform Architecture)

엔터프라이즈 환경에서 필수적인 멀티테넌시 관리, 모델 생애주기, 스마트 라우팅 및 통합 오퍼레이션 대시보드가 모두 결합된 구조입니다.

![Enterprise Architecture](/home/mingun/AI_Flatform/llm-gateway/docs/ent_architecture_img.png)

### 핵심 레이어 설명
*   **LLM API Gateway Layer**: 사용자(팀) 단위의 트래픽을 인가(Auth)하고 분당/월별 호출량을 제어(Rate Limit)합니다. 그 후 `Smart Policy Engine`을 통해 요청별로 가장 적합한 모델(비용 최적화, 속도 쵯적화 등)로 트래픽을 동적 라우팅합니다. 외부 모델 장애 시 즉각 대안 모델을 호출하는 Fallback 로직도 수행합니다.
*   **MLOps Control Plane**: 사내에 등록된 모든 LLM 모델(OpenAI, Local 등)의 메타데이터와 상태(v1.0, v2.0-dev)를 중앙 관리하는 `Model Registry`입니다.
*   **Operations & Monitoring**: Gateway에서 발생하는 트래픽 정보를 방해 없이 백그라운드로 안전하게 로깅하며, 운영팀이 언제든 열람할 수 있는 실시간 대시보드를 제공합니다.

---

## 2. 모델 평가 및 승격 워크플로우 (MLOps Workflow)

새로운 LLM(혹은 프롬프트/파라미터가 변경된 버전)이 등록되었을 때, 이를 프로덕션으로 안전하게 서비스하기 위한 자동화 파이프라인 흐름도입니다.

![Model Evaluation Workflow](/home/mingun/AI_Flatform/llm-gateway/docs/ent_workflow_img.png)

### 운영 흐름 (Lifecycle)
1. **Register Model (Dev)**: 파인튜닝되거나 새로 도입된 모델 엔드포인트가 시스템 `Model Registry`에 `dev` 상태로 등록됩니다.
2. **Auto-Eval Pipeline**: 등록 즉시 구성된 벤치마크 테스트셋이 가동되어 이전 Prod 모델보다 정확도나 지연시간 등에서 우수한지 성능을 평가합니다. (임계치 미달 시 배포 거절)
3. **Staging (Shadow Traffic)**: 통과된 모델은 `staging`으로 승격하여, 실제 사용자 트래픽의 일부(예: 5~10%)를 떼어주거나 백그라운드로 로깅용 호출만 던지는 섀도우 테스트(A/B)를 수행합니다.
4. **Promote to Prod**: 운영 모니터링상 아무런 문제가 없다면 `prod` 레벨로 최종 승격되며, Gateway의 기본 라우팅 목표(Primary target)가 됩니다.
5. **Auto-Rollback**: 승격 이후 갑작스럽게 에러 비율이 올라가거나 기준 이상의 레이턴시가 감지될 경우 시스템이 선제적으로 이전 버전으로 트래픽을 복구시킵니다.
