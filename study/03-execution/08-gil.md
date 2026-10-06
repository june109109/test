# 3-8. GIL의 범위와 예외

[목차](../README.md) · [이전](07-coroutines.md) · [정답·해설](08-gil-answers.md)

예상 50분. 목표: GIL의 적용 범위를 명시하고, I/O·네이티브 계산·free-threaded 빌드·프로세스를 구분하며, 실행 환경에 맞게 선택합니다.

## 1. 이 편의 기본 환경

기본 실습은 **GIL을 사용하는 일반적인 CPython 3.12.14, 단일 인터프리터 프로세스**입니다. GIL은 Global Interpreter Lock으로, 이 환경에서 한 시점에 하나의 스레드가 Python 코드를 실행하게 하는 주요 제약입니다. OS 스레드가 하나뿐이라는 뜻이나 프로세스 전체가 아무 형태의 병렬 연산도 못 한다는 뜻은 아닙니다.

CPython 내부 객체 관리 등의 제약과 관련된 메커니즘입니다. 앱의 모든 복합 연산을 원자적으로 만들거나 사용자 코드의 경쟁 상태를 없애는 기능으로 사용하면 안 됩니다.

## 2. 작업 종류별로 다르게 보기

| 작업·환경 | GIL이 있는 기본 환경의 관찰 | 설계 판단 |
| --- | --- | --- |
| 순수 Python 반복 계산 | 스레드 추가로 여러 코어의 Python 계산 병렬화가 제한 | 알고리즘·프로세스·적절한 네이티브 구현 비교 |
| 많은 표준 블로킹 I/O | 기다리는 동안 GIL을 해제하는 경로가 있음 | 다른 스레드의 진행으로 대기 겹침 가능 |
| GIL을 해제하는 확장 모듈 | C/C++ 등 계산이 스레드에서 병렬 가능할 수 있음 | 해당 함수·빌드·라이브러리 문서 확인 |
| 여러 프로세스 | 각 프로세스의 인터프리터 상태 분리 | 여러 CPU 예산 활용, IPC·메모리 비용 |
| free-threaded CPython | 빌드·런타임 조건에 따라 GIL 없이 실행 가능 | 호환성·동기화·성능·확장 모듈 지원 확인 |

‘I/O 함수이니 항상 GIL 해제’ 또는 ‘확장 모듈이니 항상 GIL 해제’도 과장입니다. 실제 구현이 달라집니다. 또한 GIL을 해제하는 동기 I/O라도 **이벤트루프 스레드 자체는 기다릴 수 있습니다.** GIL 해제는 다른 OS 스레드에 기회를 주는 것이지 같은 루프에서 다른 코루틴을 자동 스케줄하는 것이 아닙니다.

## 3. free-threaded에서는 무엇이 바뀌나

Python 3.13부터 선택 가능한 free-threaded 빌드가 등장했습니다. Python 버전만 보고 모든 설치에서 GIL이 없다고 결론 내리면 안 됩니다. 3.14 문서는 빌드 확인과 실제 실행 중 GIL 상태를 구분합니다. 호환되지 않은 확장 모듈을 불러오면 GIL이 다시 활성화될 수 있는 조건도 설명합니다.

새 런타임에서 `sys._is_gil_enabled()`가 제공되면 실제 상태를 확인할 수 있습니다. `sysconfig.get_config_var("Py_GIL_DISABLED")`는 빌드 지원 확인에 쓰입니다. 3.12처럼 없는 API를 직접 호출하면 안 됩니다.

```python
import sys
import sysconfig

probe = getattr(sys, "_is_gil_enabled", None)
print("free-threaded build:", sysconfig.get_config_var("Py_GIL_DISABLED"))
print("runtime GIL:", probe() if probe else "probe unavailable; inspect version/build")
```

free-threaded에서도 메모리·락·라이브러리·CPU quota의 한계는 남습니다. 내장 컨테이너의 내부 잠금이 앱의 여러 단계 업무 규칙을 자동 보호하지 않습니다. 단일 스레드 성능과 메모리 비용도 작업에 따라 달라 실측해야 합니다.

## 4. 프로세스로 옮길 때의 추가 조건

ProcessPoolExecutor는 별도 프로세스에서 함수를 실행하고 입력·출력을 직렬화해 전달합니다. 모듈 최상위 함수와 직렬화 가능한 값을 사용하는 편이 명확합니다. 노트북·REPL의 함수와 lambda가 그대로 동작한다고 가정하지 않습니다.

`if __name__ == "__main__":` 보호를 두고 시작 방식을 명시하거나 배포 버전의 기본값을 확인합니다. Python 3.14에서는 fork가 어느 플랫폼에서도 기본값이 아니며 POSIX의 기본이 forkserver로 바뀐 환경이 있습니다. Windows·macOS의 spawn, 사용 가능한 시작 방식 차이도 확인합니다. 이 자료의 실험은 비교를 위해 **spawn을 명시**합니다.

멀티스레드 프로세스를 fork하거나 이미 열린 소켓·DB 클라이언트를 상속하면 안전성 문제가 생길 수 있습니다. 워커에서 필요한 자원을 적절히 초기화하고 종료하세요. 프로세스를 쓴다는 사실만으로 안전한 격리가 완성되지는 않습니다.

## 5. 판단 사례

순수 Python 계산이 작고 결과를 넘기는 비용이 크면 프로세스가 더 느릴 수 있습니다. NumPy 같은 라이브러리의 특정 연산이 GIL을 해제하고 내부 스레드도 쓴다면 외부 프로세스를 더 늘려 과도한 병렬성을 만들 수 있습니다. 제품 이름만이 아니라 실제 함수·스레드 설정·자원 한도를 봅니다.

기존 안정적인 GIL 환경에서 I/O가 병목인 서비스를 free-threaded로 바꾸는 것만으로 큰 개선을 기대할 근거는 부족합니다. 필요한 효과와 호환성 검증 비용을 비교하세요.

## 적용 과제

현재 실행 환경의 버전·구현·빌드 정보를 기록하고, 사용 중인 CPU 집약 함수 하나의 구현이 순수 Python인지 네이티브인지 확인할 계획을 쓰세요. 스레드·프로세스·free-threaded 중 두 대안을 비교하되 실행하지 않은 벤치마크 결과를 가정으로 쓰지 않습니다.

### Python 트랙 보강: 선택을 바꾸는 네 가지 질문

1. GIL이 있는 CPython의 Python 계산인가? 프로세스가 병렬 후보이지만 입력 직렬화·복사·시작 비용을 포함합니다.
2. I/O를 기다리는가? 스레드 또는 지원되는 async API가 후보입니다. GIL 해제가 현재 이벤트루프의 다음 task 실행을 대신하지는 않습니다.
3. NumPy 등 확장 모듈이 GIL을 놓고 자체 스레드를 사용하는가? 프로세스까지 늘리면 내부 스레드×프로세스의 과도한 경쟁이 생길 수 있습니다.
4. free-threaded 빌드인가? 확장 모듈 호환·GIL 재활성화·공유 상태의 동기화와 실제 런타임 상태를 확인합니다.

작업 크기가 작은 CPU 함수는 프로세스 전달 비용 때문에 더 느릴 수 있습니다. [3-9](09-benchmark.md)의 결과를 읽을 때 함수 계산과 풀 준비 비용을 나누고, 운영 선택에서는 둘을 합친 사용자 지연도 다시 계산하세요.

## 퀴즈

Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 권장 통과 8점이며 Q3를 중요하게 봅니다.

### Q1
CPython에서 스레드는 I/O 작업 병행에도 항상 쓸모없나요?

### Q2
Python 3.13 이상이면 모든 설치에서 GIL이 꺼져 있나요?

### Q3
동기 SDK가 I/O 중 GIL을 해제합니다. async 함수에서 직접 호출해도 루프가 막히지 않는다는 결론이 맞나요?

### Q4
프로세스 풀을 도입할 때 CPU 수 외에 확인할 조건 두 가지를 적으세요.

### Q5
순수 Python CPU 작업을 스레드풀로 옮겼는데 빨라지지 않았습니다. 원인 가설, 대안 둘, 측정 환경·비용·호환성 검증을 설명하세요.

## 출처

2026-10-01 확인. 버전별 적용 범위를 구분했습니다.

- [CPython 3.12 threading](https://github.com/python/cpython/blob/3.12/Doc/library/threading.rst): GIL과 CPU/I/O 기본 설명.
- [CPython 3.12 asyncio task](https://github.com/python/cpython/blob/3.12/Doc/library/asyncio-task.rst): to_thread와 GIL 해제 확장 모듈의 예외.
- [CPython 3.14 free-threading how-to](https://github.com/python/cpython/blob/3.14/Doc/howto/free-threading-python.rst): 빌드·런타임 GIL, 확장 모듈, 동기화.
- [CPython 3.14 multiprocessing](https://github.com/python/cpython/blob/3.14/Doc/library/multiprocessing.rst): 시작 방식과 버전 변화.
