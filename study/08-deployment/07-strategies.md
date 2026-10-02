# 8-7. 배포 전략과 종료 절차

[목차](../README.md) · [정답·해설](07-strategies-answers.md)

예상 55분. 목표: rolling·blue-green·canary의 교환 비용을 비교하고, 트래픽 제외와 프로세스 종료 사이를 설계합니다.

## 1. 전략별 비용

| 전략 | 진행 | 이익 | 비용·주의 |
| --- | --- | --- | --- |
| rolling | 일부씩 새 버전으로 교체 | 추가 자원 제한 가능 | 버전 혼재·최저 가용 수·느린 롤백 |
| blue-green | 두 환경 준비 후 전환 | 명확한 전환·빠른 경로 복구 | 중복 자원·DB 호환·기존 연결 |
| canary | 일부 트래픽으로 새 버전 검증 | 영향 범위 제한·실사용 관측 | 라우팅·표본·분석·자동 중단 |

canary 1%에서 오류가 없었다고 드문 기능이나 특정 테넌트가 정상이라는 증거는 아닙니다. 비교군·표본 크기·관찰 시간·공통 외부 장애를 고려합니다. blue-green도 DB를 공유하면 앱만 되돌려 데이터 변경을 취소할 수 없습니다.

## 2. probe의 서로 다른 질문

startup probe는 앱이 초기화될 시간을 줍니다. readiness는 지금 새 트래픽을 받을 준비가 되었는지, liveness는 프로세스를 재시작해야 하는 상태인지에 관한 검사입니다. 모든 외부 DB 장애를 liveness 실패로 연결하면 전체 앱이 재시작하며 상황을 악화시킬 수 있습니다.

health endpoint의 200은 시작점입니다. 실제 의존성·대표 기능·권한·데이터 호환·지표를 추가 확인합니다. 검사 자체가 DB 과부하를 만들지 않게 비용을 제한합니다.

## 3. graceful shutdown 순서

```text
새 트래픽 대상에서 제외
  → 전파/기존 연결에 따른 유입 고려
  → 신규 작업 수락 중단 또는 제한
  → 진행 중 요청·작업을 정해진 시간까지 기다림
  → 풀·클라이언트·로그 등 자원 종료
  → 제한 초과 시 강제 종료와 미완료 처리
```

이 절차는 실제 플랫폼의 종료 신호·endpoint 반영·프록시 drain 동작에 맞춰야 합니다. 단순히 sleep 10초를 넣으면 모든 요청이 끝난다는 보장은 없습니다. WebSocket·SSE·긴 업로드·백그라운드 작업은 별도 종료 계약을 갖습니다.

컨테이너의 PID 1에 신호가 제대로 전달되도록 exec 형식 entrypoint 등을 사용합니다. grace period가 앱 정리보다 짧으면 종료 중간에 강제 중단될 수 있습니다. 요청 취소 후 스레드가 남는 문제는 7-4와 연결됩니다.

## 4. DB 변경은 expand-contract

먼저 구·신버전이 함께 읽을 수 있는 새 컬럼/구조를 추가하고, 호환 가능한 코드를 배포하고, 필요한 데이터를 채운 뒤, 더 이상 구버전이 없을 때 이전 구조를 제거합니다. 컬럼 rename/drop을 앱 교체와 한 번에 하면 rolling 중 구버전이 실패할 수 있습니다.

backfill 비용·락·이중 쓰기·복구도 설계해야 합니다. 모든 변경이 쉽게 되돌릴 수 있는 것은 아닙니다. rollback 가능 구간과 forward fix가 필요한 구간을 명시합니다.

## 5. 적용 과제

일반 요청 p99 2초, 최대 업로드 2분인 서비스의 drain·grace·재시도 계약을 만드세요. DB 컬럼을 바꾸는 배포에서 구버전·신버전·backfill이 공존하는 순서도 적습니다.

## 퀴즈

### Q1

blue-green이면 DB 변경도 즉시 안전하게 rollback되는가?

### Q2

readiness와 liveness는 같은 질문인가?

### Q3

canary의 이익과 표본 한계를 설명하라.

### Q4

종료 전에 트래픽 제외와 drain을 하는 이유는?

### Q5

컬럼 변경과 긴 요청이 있는 서비스의 rolling 배포·복구를 설계하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [Kubernetes Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) — rolling의 maxUnavailable·maxSurge. 종료 중 Pod 때문에 실제 순간 자원이 단순 replicas+surge를 넘을 수도 있음을 확인했습니다.
- [Pod lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/) — 종료·probe 계약의 후속 읽기.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
