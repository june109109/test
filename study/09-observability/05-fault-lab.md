# 9-5. 고장을 주입하고 관찰하기

[목차](../README.md) · [정답·해설](05-fault-lab-answers.md)

예상 65분. 목표: 의도적으로 만든 병목의 원인과 지표를 연결하고, 실험 범위를 보존합니다.

## 1. 실행 방법

[코드](../labs/observability.py), [결과](../results/observability-2026-10-02.json), [그래프 생성 코드](../labs/plot_observability.py).

```bash
python3 study/labs/observability.py --output /tmp/observe-new.json
MPLCONFIGDIR=/tmp/study-mpl XDG_CACHE_HOME=/tmp/study-plot-cache   python3 study/labs/plot_observability.py /tmp/observe-new.json /tmp/observe-new.png
```

본문 실험은 AnyIO, 그래프는 Matplotlib 3.10.8이 필요합니다. Python 가상환경에 설치하고 새 출력 경로를 사용하세요. 실제 측정은 2026-10-02에 수행했습니다. 프로덕션 서비스에 장애를 주입하는 코드가 아니라 자체 프로세스의 유한한 작업입니다.

## 2. 가설과 조작

| 실험 | 바꾼 것 | 관찰할 것 |
| --- | --- | --- |
| loop blocking | 루프에서 time.sleep(60ms) | heartbeat가 늦어짐 |
| offload | 같은 sleep을 to_thread로 이동 | 루프가 계속 heartbeat 처리 |
| thread limiter | AnyIO 토큰 2, 작업 6, 각 sleep30ms | 최대 borrowed2, 나머지 대기 |

루프 실험은 task를 먼저 동작시켜 표본을 수집한 뒤 sleep을 넣습니다. 풀 실험은 기존 limiter 값을 저장하고 실험 후 복원합니다. 풀의 토큰을 바꾸는 것이 전역 OS 스레드 수를 바꾸는 것은 아닙니다.

## 3. 실제 관찰

| 항목 | 값 |
| --- | --- |
| blocking 최대 loop lag | 약 60.284ms |
| offloaded 최대 loop lag | 약 0.798ms |
| limiter 설정 / peak borrowed | 2 / 2 |
| 작업 완료 | 6 / 6 |

첫 두 값은 단일 짧은 실행의 최대 관찰값입니다. 플랫폼 스케줄링 때문에 다음 실행에서 수치가 달라집니다. offload가 모든 작업을 빠르게 하거나 thread cost가 없다는 결론이 아닙니다. waiting을 어느 스레드에서 하는지가 루프 반응성에 영향을 준다는 증거입니다.

## 4. 실제 대시보드로 옮길 때

지금 그래프는 저장된 표본입니다. Prometheus exporter를 붙이면 지연 histogram·limiter gauge·요청 오류·duration을 주기적으로 수집할 수 있습니다. 멀티프로세스 Python client의 registry/수집 방식은 단일 프로세스와 다르므로 공식 multiprocess 모드를 확인해야 합니다.

Grafana에는 같은 시간 범위의 요청 지연·loop lag·tokens·CPU·DB wait를 배치하고 실험 시작/종료 표시를 남깁니다. 여기서는 Prometheus/Grafana/OTel collector를 실제로 띄우지 않았습니다. 수집 간격이 짧은 고장을 놓칠 수 있으므로 histogram과 앱 이벤트 로그로 보완합니다.

## 5. 적용 과제

실제 앱의 테스트 환경에서 느린 SDK, DB 풀 대기, CPU 부하를 각각 하나씩 주입할 실험서를 만드세요. 중단 조건·최대 시간·대상 범위·복구 확인을 적고 모든 변수를 동시에 바꾸지 않습니다.

보강: 실제 prometheus-client exporter·Prometheus 설정·Grafana 가져오기 파일과 실행 범위는 [9-7](07-live-metrics.md)에 추가했습니다.

## 퀴즈

### Q1

저장된 그래프는 실시간 Grafana를 실행한 증거인가?

### Q2

offloaded 표본의 최대 lag가 0.798ms면 항상 그 이하가 보장되는가?

### Q3

두 sleep 실험에서 통제한 것과 바꾼 것은?

### Q4

limiter 복원이 필요한 이유와 확인한 완료 수는?

### Q5

느린 SDK를 테스트 앱에 주입하는 관측·중단·복구 계획을 작성하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- 원본 측정은 [JSON](../results/observability-2026-10-02.json)에 보존했습니다.
- [Prometheus Python client](https://prometheus.github.io/client_python/)는 실제 수집기로 옮길 때의 후속 읽기입니다.

확인일: 2026-10-02. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
