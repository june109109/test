# 9-7. Python 지표를 Prometheus·Grafana로 연결하기

[목차](../README.md) · [정답·해설](07-live-metrics-answers.md)

예상 90분. 목표: 저장된 그래프에서 한 단계 더 나아가 exporter·수집기·대시보드의 계약을 연결하고, 루프 막힘과 토큰 포화를 관측합니다.

## 1. 추가한 것과 실제 검증 범위

[FastAPI exporter](../labs/metrics_app.py), [유한한 부하 발생기](../labs/drive_metrics.py), [Prometheus 설정](../labs/monitoring/prometheus.yml), [Grafana 가져오기 JSON](../labs/monitoring/grafana-dashboard.json)을 제공합니다.

2026-10-06에 실제 실행한 것은 **exporter의 in-process ASGI 테스트**입니다. loop lag histogram, AnyIO 토큰 2개, 6개 요청 완료, 메트릭 응답, RSS 메트릭, delay 범위 422를 확인했습니다. Prometheus/Grafana 서버를 띄워 scrape·대시보드 렌더링까지 검증한 것은 아닙니다. 아래는 독자가 이어서 실행할 연결 절차입니다. JSON 문법 확인과 실제 제품 호환 검증도 다릅니다.

## 2. 준비와 앱 실행

저장소 루트에서 가상환경을 만들고 [의존성](../labs/requirements-python-track.txt)을 설치합니다. 기존 4·10장 패키지와 prometheus-client 0.21.1 등을 고정합니다. 전체 전이 의존성 lock은 아닙니다.

```bash
python3 -m venv /tmp/study-track
/tmp/study-track/bin/python -m pip install -r study/labs/requirements-python-track.txt
/tmp/study-track/bin/python -m uvicorn metrics_app:create_app --factory   --app-dir study/labs --host 127.0.0.1 --port 8008 --workers 1
```

별도 터미널에서 `curl http://127.0.0.1:8008/health`와 `/metrics`를 확인합니다. 포트가 이미 사용 중이면 기존 프로세스를 임의로 죽이지 말고 앱·수집기·발생기의 포트를 함께 바꿉니다. 고장 주입 endpoint는 0~0.5초 대기만 허용하며 loopback 학습용으로 제한합니다.

## 3. 지표의 정의

| 메트릭 | 의미 | 함정 |
| --- | --- | --- |
| study_loop_lag_seconds | 10ms sampler의 초과 지연 histogram | 원인 자체를 알려주지 않음 |
| study_thread_tokens_borrowed/total | 같은 AnyIO limiter의 사용/한도 | 모든 OS 스레드 아님 |
| study_thread_route_inflight | thread 경로 진행 요청, 토큰 대기 포함 | borrowed와 차이는 대기 근사이지 정확한 큐 계측 아님 |
| process_resident_memory_bytes | exporter 프로세스의 RSS | 여러 워커 합·Python 객체만의 크기 아님 |
| study_http_requests_total | 완료 요청의 route/status별 누적 | /metrics는 제외, 전체 URL을 라벨로 쓰지 않음 |
| study_http_duration_seconds | 앱 middleware 경과 시간 | 클라이언트 TCP/TLS 전체 지연 아님 |

이 앱은 **1워커 전용**입니다. 같은 포트로 여러 워커를 띄우면 매 scrape가 다른 프로세스로 가서 counter가 뒤섞일 수 있습니다. 여러 독립 인스턴스를 각각 target으로 노출하거나 prometheus-client의 지원되는 multiprocess 모드와 cleanup·metric 제약을 별도로 설계합니다. PID를 붙이는 것만으로 누락된 워커 수집이 해결되지는 않습니다.

## 4. 수집기와 대시보드 연결

이 절차는 앱·Prometheus·Grafana가 **같은 머신의 프로세스**라는 전제입니다. 컨테이너의 127.0.0.1은 서로 다르므로 컨테이너 배치에는 target과 datasource 주소를 그 환경에 맞춰 바꿔야 합니다.

설치된 Prometheus에서 다음을 실행합니다. 바이너리 설치와 Grafana 서비스 구동은 이 실습에서 자동화하지 않았으며 해당 제품의 설치 절차가 선행 조건입니다.

```bash
prometheus --config.file=study/labs/monitoring/prometheus.yml   --web.listen-address=127.0.0.1:9090 --storage.tsdb.path=/tmp/study-prometheus-data
```

Prometheus Targets에서 study-python이 UP인지 확인합니다. Grafana에는 Prometheus 데이터 소스 URL을 `http://127.0.0.1:9090`으로 등록하고 제공한 JSON을 Import한 뒤 `DS_PROMETHEUS`를 선택합니다. datasource 접속은 Grafana 서버 관점입니다. 6개 패널은 loop lag p99, 토큰과 진행 요청, RSS, 요청률, p95 handler 시간, target 건강을 보여줍니다.

histogram_quantile에는 bucket별 rate를 합산한 분포를 사용합니다. 워커별 p99를 평균하지 않습니다. rate[1m]은 최근 1분의 변화를 사용하므로 새로 시작한 직후에는 표본이 없거나 불안정할 수 있습니다.

## 5. 한 변수씩 고장 주입

```bash
/tmp/study-track/bin/python study/labs/drive_metrics.py --mode block --seconds 30
/tmp/study-track/bin/python study/labs/drive_metrics.py --mode thread --seconds 30
```

각 명령을 따로 실행하고 중간 회복 구간을 둡니다. block은 사용자 1명, thread는 사용자 8명이고 각 요청은 100ms 합성 대기입니다. block에서는 lag가 늘어나는지, thread에서는 토큰 2에 진행 요청이 더 많고 lag는 상대적으로 작은지 확인합니다. 이는 예상 관찰이며 실제 대시보드 값을 미리 보장하지 않습니다. scrape보다 짧은 포화는 gauge가 놓칠 수 있어 histogram·구간 로그로 보완합니다.

끝나면 자신이 시작한 앱·수집기만 종료합니다. 원본 측정·도구 버전·설정·오류·정리 결과를 기록합니다. 이 드라이버는 유한한 고장 관찰용이며 11장의 용량 benchmark를 대신하지 않습니다.

## 6. OpenTelemetry를 함께 사용할 때

Prometheus는 집계 추세, trace는 한 요청의 내부 경로를 설명합니다. OTel을 쓰려면 SDK/TracerProvider→span processor→exporter→Collector/trace 저장소→조회 도구라는 경로가 필요합니다. FastAPI 자동 계측만 설치하고 collector가 없으면 trace가 저장되었다고 볼 수 없습니다.

요청 span 아래에 SDK·DB span을 붙이되 중복 자동 계측을 피하고, trace context의 전파·sampling·개인정보 제외·종료 시 flush를 정합니다. OTel collector/자동 계측의 실행은 이번 추가 테스트에 포함하지 않았습니다. boto3의 호출 시간 span을 ‘커넥션 풀 획득 대기’로 이름 붙이지 말고 4-6의 실제 pool 구현을 확인하세요.

## 퀴즈

### Q1

이 편의 실제 테스트는 Grafana 화면 렌더링까지 검증했는가?

### Q2

워커 4개를 같은 포트에 띄우고 이 exporter를 그대로 scrape하면 전부 집계되는가?

### Q3

루프 막힘과 토큰 포화를 어떤 지표 조합으로 구분할 것인가?

### Q4

boto3 호출 시간을 풀 획득 대기라고 이름 붙이면 안 되는 이유는?

### Q5

앱→수집기→Grafana와 선택적 OTel 경로의 검증·실험·정리를 설계하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [Prometheus Python client](https://prometheus.github.io/client_python/)와 [multiprocess](https://prometheus.github.io/client_python/multiprocess/)는 수집을 확장할 때 참고할 문서입니다.
- 직접 확인: prometheus-client 0.21.1을 설치하고 제공한 exporter의 지표 응답을 테스트했습니다.
- [실행 기록](../results/python-track-2026-10-06.xml).

확인일: 2026-10-06. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
