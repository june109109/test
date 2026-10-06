# 8-3. 컨테이너 자원과 워커 수

[목차](../README.md) · [정답·해설](03-resources-answers.md)

예상 50분. 목표: 호스트 CPU 개수·affinity·quota를 구분하고, CPU와 메모리로 워커 예산을 잡습니다.

## 1. CPU가 16개 보이는데 왜 느릴까

`os.cpu_count()`는 런타임·환경에 따라 호스트의 논리 CPU 개수를 보여 줄 수 있습니다. 그 컨테이너에 허용된 CPU 시간 예산과 같다는 보장이 없습니다. affinity/cpuset은 실행 가능한 CPU 집합이고 quota는 기간당 사용할 CPU 시간 한도입니다.

cgroup v2의 `cpu.max`가 `200000 100000`이면 100ms 기간당 총 200ms의 CPU 시간을 쓸 수 있는 설정으로, 약 2 CPU 상당의 시간 예산입니다. 전용 코어 2개를 독점한다는 뜻은 아닙니다. `max`는 그 cgroup 수준의 quota가 없다는 뜻이며 부모 계층 제한은 별도로 존재할 수 있습니다.

## 2. 실제 앞선 실험 환경

3-9의 저장 결과는 CPython 3.12.14, 보이는 CPU 5, affinity 5, cpu.max `400000 100000`이었습니다. 따라서 당시 시간 예산은 약 4 CPU 상당이었으며 ‘독점 코어 5개’로 해석하지 않았습니다. 이후 실행 환경이나 컨테이너마다 값이 달라질 수 있습니다.

Python 3.13+에는 `os.process_cpu_count()` 등 다른 API도 있지만 모든 quota를 정확히 반영한다고 버전 확인 없이 단정하지 않습니다. OS 제한 파일·runtime 문서·실제 throttling 지표를 함께 봅니다.

## 3. 워커 예산

CPU-heavy 작업은 워커를 quota보다 훨씬 늘려도 총 계산 예산이 늘지 않습니다. I/O-heavy 작업은 한 이벤트루프에서 많은 대기를 병행할 수 있지만 블로킹 코드·스레드풀·하류 연결이 한계를 만듭니다.

메모리도 중요합니다. 워커별 힙·모듈·캐시·풀 버퍼가 복제됩니다. RSS 합은 공유 페이지를 중복 셀 수 있고 실제 cgroup memory 사용은 다른 항목도 포함하므로 단순 합과 차이를 이해해야 합니다.

설명용으로 컨테이너 1GiB에서 공통 여유 256MiB, 워커당 피크 추가 200MiB라면 세 워커가 856MiB로 들어갈 수 있지만 네 워커는 1056MiB로 넘습니다. 이 추정은 공유/캐시·burst를 단순화하므로 부하 중 실제 memory.current·OOM·RSS/PSS를 확인해야 합니다.

## 4. 선택 비교

| 조정 | 기대 효과 | 비용 |
| --- | --- | --- |
| 워커 증가 | CPU 활용·프로세스 격리 | 메모리·풀·컨텍스트 전환 |
| CPU quota 증가 | 사용 가능한 계산 시간 증가 | 비용·스케줄링 조건 |
| 비동기화/블로킹 제거 | 기다림 동안 다른 요청 진행 | 코드·라이브러리 변경 |
| 별도 작업 프로세스/큐 | 긴 CPU 작업 격리 | 전달·재시도·상태·운영 |

컨테이너 하나당 워커 하나가 오케스트레이션을 단순하게 할 수 있지만 항상 정답은 아닙니다. 컨테이너 수 증가도 각 풀과 사이드카 등의 비용을 늘립니다.

## 5. 적용 과제

quota 2 CPU, 메모리 1GiB, 평균 I/O 대기 200ms인 API를 워커 1·2·4로 비교할 실험을 설계하세요. RPS뿐 아니라 throttling·p99·오류·메모리·DB 연결 예산을 포함합니다.

### Python 트랙 보강: 읽기 전용 환경 점검

```python
import os
from pathlib import Path
print("logical", os.cpu_count())
print("affinity", len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else "unsupported")
p = Path("/sys/fs/cgroup/cpu.max")
print("cgroup-v2 quota", p.read_text().strip() if p.exists() else "inspect platform cgroup layout")
```

독자가 자신의 컨테이너에서 실행할 읽기 전용 조각입니다. cgroup v1·다른 mount·부모 제한에서는 이 경로 하나로 전체 제한을 알 수 없습니다. 프로세스 API가 알려주는 값, quota와 throttling, 워커별 RSS를 함께 기록하세요. worker 수만 바꿀 때 DB풀·로컬 캐시도 복제되므로 CPU 최적화가 메모리/DB 장애를 만들지 않게 예산을 확인합니다.

## 퀴즈

### Q1

cpu.max의 2 CPU 상당은 전용 코어 2개 보장인가?

### Q2

os.cpu_count만으로 컨테이너 워커 수를 확정해도 되는가?

### Q3

affinity/cpuset과 quota의 차이를 설명하라.

### Q4

워커 증가의 CPU 외 비용 두 가지는?

### Q5

CPU 2·메모리 1GiB의 워커 수를 결정하는 측정 계획을 제안하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [Linux cgroup v2 CPU interface](https://docs.kernel.org/admin-guide/cgroup-v2.html) — 후속 읽기.
- [3-9 원본 환경](../results/concurrency-2026-10-01.json) — 이 자료에서 실제 관찰한 값.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
