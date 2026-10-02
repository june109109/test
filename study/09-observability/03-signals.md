# 9-3. 로그·메트릭·트레이스

[목차](../README.md) · [정답·해설](03-signals-answers.md)

예상 50분. 목표: 각 신호가 답하는 질문과 저장 비용을 구분하고, Prometheus·OpenTelemetry·Grafana의 역할을 연결합니다.

## 1. 서로 다른 질문

로그는 특정 사건의 상세를, 메트릭은 시간에 따른 집계된 상태를, trace는 한 작업이 여러 단계·서비스를 거치는 경로와 시간을 보여 줍니다. 어느 하나가 나머지를 모두 대체하지 않습니다.

| 질문 | 우선 신호 | 한계 |
| --- | --- | --- |
| 오류율이 언제 늘었나 | 메트릭 | 개별 원인 상세 부족 |
| 이 결제는 왜 실패했나 | 로그/trace | 보존·샘플링에 따라 누락 |
| 지연 중 어디서 기다렸나 | trace+구간 메트릭 | 계측 없는 구간은 공백 |
| CPU를 어떤 함수가 썼나 | profile | 요청 경로와 자동 연결은 별도 |

## 2. 도구의 역할

Prometheus는 시계열 수집·저장·질의에 흔히 사용됩니다. `prometheus-client`는 앱에서 counter·gauge·histogram 등을 노출하는 계측 라이브러리입니다. Grafana는 데이터 소스의 결과를 시각화하는 도구이며 메트릭 저장소 자체와 같지 않습니다.

OpenTelemetry는 trace/metric/log의 계측·전파·export를 위한 API·SDK·프로토콜과 collector 생태계를 제공합니다. trace를 붙였다고 저장·샘플링·민감정보·서비스 명명 정책까지 완성되지는 않습니다.

## 3. label cardinality

`http_requests_total{method="GET",route="/orders/{id}",status="200"}`처럼 제한된 라벨 조합은 집계에 적합합니다. user_id·request_id·전체 URL을 라벨로 넣으면 값 종류가 요청만큼 늘어나 저장·메모리·질의 비용이 폭증할 수 있습니다.

서비스 10×경로100×상태10×인스턴스20이면 최대 200,000조합입니다. 실제 생성 조합은 다를 수 있지만 곱셈이 어떻게 커지는지 계산해야 합니다. 고유 ID는 로그/trace와 exemplars 같은 연결 기능을 검토합니다.

## 4. counter·gauge·histogram

counter는 누적 사건 수이며 재시작 때 리셋될 수 있습니다. gauge는 현재 활성 요청·사용량처럼 오르내리는 값입니다. histogram은 지연 분포를 bucket 등으로 집계하며 bucket 경계가 정밀도를 결정합니다.

워커별 p99를 단순 평균해 전체 p99를 만들 수 없습니다. 호환되는 histogram bucket/count를 합쳐 전체 분포를 계산하거나 지원되는 집계 방식을 사용합니다. 평균 지연만으로 긴 꼬리를 설명하지 않습니다.

## 5. 적용 과제

요청률·오류율·지연 분포, pool wait, loop lag를 한 화면에 배치하고, 오류가 늘면 어떤 로그/trace로 이동할지 설계하세요. 라벨의 값 종류와 보존 비용도 적습니다. 이 편은 Grafana 서버를 설치한 결과가 아니라 관측 설계입니다.

## 퀴즈

### Q1

Grafana는 언제나 메트릭 저장소 자체인가?

### Q2

request-id를 메트릭 라벨로 넣으면 어떤 비용이 생기는가?

### Q3

로그·메트릭·trace가 답하는 질문을 하나씩 들어라.

### Q4

워커 p99 평균으로 전체 p99를 계산하면 안 되는 이유는?

### Q5

FastAPI API의 관측 신호·라벨·연결 경로를 설계하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [Prometheus instrumentation practices](https://prometheus.io/docs/practices/instrumentation/) — 후속 읽기.
- [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/) — 후속 읽기. 실제 수집기·Grafana 설치 검증은 수행하지 않았습니다.

확인일: 2026-10-02. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
