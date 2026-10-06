# 9-6. 프로파일링 도구 선택

[목차](../README.md) · [정답·해설](06-profiling-answers.md)

예상 50분. 목표: CPU 시간·Python 할당·native 메모리를 구분해 도구를 선택합니다.

## 1. 무엇이 궁금한가

‘메모리가 커진다’는 현상에는 Python 객체 유지, native 확장 할당, allocator가 OS에 반환하지 않은 공간, mmap, 워커 복제 등 여러 원인이 있습니다. ‘느리다’도 CPU 계산과 기다림이 다릅니다. 질문과 측정 범위를 먼저 정합니다.

| 도구 | 주로 보는 것 | 비용·한계 |
| --- | --- | --- |
| py-spy | 실행 중 Python stack의 샘플·시간 분포 | attach 권한·샘플 편향·native 옵션 |
| tracemalloc | Python이 추적하는 할당의 위치·변화 | 시작 이전 할당과 추적 밖 native 메모리 한계 |
| memray | Python/native allocator 경로의 메모리 프로파일 | 수집 방식·권한·오버헤드·파일 크기 |
| cProfile | 함수 호출/실행 시간 계측 | 계측 오버헤드·비동기 해석 주의 |
| OS RSS/PSS/cgroup | 프로세스·컨테이너 메모리 | 어떤 코드가 보유하는지 직접 설명 못함 |

## 2. CPU와 대기

샘플링 프로파일은 어떤 stack이 자주 관찰되는지 보여 줍니다. CPU-heavy 코드에서는 핫스팟을 찾기 좋지만, 대기 시간을 CPU 계산 시간과 혼동하지 않도록 도구 옵션과 표본 수집 방식을 확인합니다. 요청 경로·trace와 결합하면 더 잘 해석할 수 있습니다.

실행 중 attach는 대상 PID가 정확한지, 허용된 환경인지 확인합니다. 컨테이너의 ptrace 정책·권한이 필요할 수 있습니다. 권한 실패를 해결하려고 모든 컨테이너를 무조건 privileged로 바꾸는 방식은 피합니다.

## 3. 실제 tracemalloc 관찰

관측 실습은 추적을 시작하고 snapshot을 찍은 뒤, 1,024바이트 bytearray 1,000개를 리스트에 유지하고 다시 snapshot을 찍었습니다. 실제 추적 크기 차이는 **1,090,424바이트**였습니다.

payload 1,024,000바이트보다 큰 이유에는 객체·리스트 등 Python 할당과 측정 관련 비용이 포함됩니다. 이 수치는 RSS 증가량이 아니며 모든 native 할당의 총합도 아닙니다. 객체 수와 예상 payload보다 큰 양의 변화라는 조건을 확인했습니다. 이 실험은 의도적으로 유지한 할당이며 실제 메모리 누수를 발견한 것이 아닙니다.

## 4. 누수 조사 절차

같은 업무를 반복하고 안정화 후 여러 snapshot을 비교합니다. 어떤 traceback의 살아 있는 할당이 계속 늘어나는지 확인하고, 해당 객체를 누가 참조하는지 조사합니다. peak 사용량이 높다는 사실과 시간이 지나도 회수되지 않는 누적 증가는 다릅니다.

tracemalloc 변화는 작지만 RSS가 커지면 native 라이브러리·allocator·mmap·공유 페이지 등 다른 범위를 조사합니다. 프로파일링 자체가 성능에 영향을 주므로 짧은 대표 구간과 전후 부하를 기록합니다.

## 5. 적용 과제

CPU100%+RSS안정, CPU낮음+p99높음, Python추적안정+RSS증가의 세 증상에 도구와 다음 질문을 하나씩 정하세요. py-spy와 memray는 이번 환경에서 실행하지 않았습니다.

### Python 트랙 보강: 도구를 실행하기 전에 정할 것

실행 중인 자신의 테스트 프로세스 PID를 확인한 후 `py-spy dump --pid <PID>`로 현재 stack을 보고, 일정 시간의 profile은 `py-spy record --pid <PID> --duration 30 -o /tmp/study-profile.svg` 같은 형태로 수집합니다. 이 명령은 사용 형태이며 이번 보강에서 py-spy를 설치/실행하지 않았습니다. attach 권한·도구 버전·컨테이너 PID namespace를 먼저 확인합니다.

할당 원인에는 tracemalloc snapshot 차이, native 범위가 필요하면 `python -m memray run --native -o /tmp/study-memory.bin your_program.py`가 후보입니다. memray도 미실행 예시이며 해당 프로그램은 독자의 유한한 실습 프로그램으로 대체합니다. flamegraph의 넓이는 설정에 따른 표본/비용이며 모든 경우의 벽시계 지연과 같지 않습니다. 메모리 peak, 누적 allocation, 살아 있는 allocation, RSS 중 무엇을 보는지 보고서에 적으세요.

## 퀴즈

### Q1

tracemalloc의 추적 바이트는 RSS와 항상 같은가?

### Q2

의도적으로 유지한 큰 리스트를 관찰하면 즉시 메모리 누수 증거인가?

### Q3

py-spy와 tracemalloc의 주된 질문 차이는?

### Q4

추적 할당이 안정적인데 RSS가 늘 때 조사할 범위 두 가지는?

### Q5

반복 요청 중 메모리 증가를 조사할 측정·가설·검증 계획을 제안하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [Python tracemalloc](https://docs.python.org/3/library/tracemalloc.html).
- [py-spy](https://github.com/benfred/py-spy), [Memray](https://bloomberg.github.io/memray/)는 후속 도구 문서입니다. 실제 실행한 도구는 tracemalloc과 내부 probe입니다.

확인일: 2026-10-02. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
