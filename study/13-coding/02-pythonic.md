# 13-2. 파이썬스러움과 과한 마법

[목차](../README.md) · [정답·해설](02-pythonic-answers.md)

예상 55분. 목표: comprehension·generator·context manager를 수명과 오류 시점까지 고려해 선택합니다.

## 1. 표현이 짧아져도 정책은 보여야 한다

단순 변환·필터에는 comprehension이 잘 맞습니다. 깊은 중첩·부작용·여러 예외 처리까지 넣으면 일반for문이 더 읽기 쉬울 수 있습니다.

```python
active_names = [user.name for user in users if user.active]
```

이름이 명확한 짧은 예입니다. 네트워크 호출·로그 기록·상태 변경을 한 comprehension 안에 섞는다면 순서·실패·재시도를 드러내는 loop나 함수로 나눕니다. PEP20의 가독성은 ‘한 줄로 만들기’와 같은 뜻이 아닙니다.

## 2. list와 generator

| 선택 | 이익 | 감수할 것 |
| --- | --- | --- |
| list | 반복·인덱싱·즉시 결과/오류 | 전체 결과 메모리 |
| generator | 필요한 만큼 계산·메모리 절약 | 일회 소비·오류 지연·수명 |
| iterator를 list로 변환 | 여러 번 사용 가능 | lazy 이익 감소·전체 materialize |

```python
values = (n * 2 for n in range(3))
first = list(values)   # [0, 2, 4]
second = list(values)  # []: 이미 소비함
```

generator를 만들어 두고 원본 mutable 데이터가 변한 뒤 소비하면 예상과 다른 시점의 값을 볼 수 있습니다. generator가 파일·DB커서를 잡고 오래 살아 있으면 자원도 오래 점유할 수 있습니다.

## 3. 파일의 소유권을 보이게

```python
def nonempty_lines(stream):
    for line in stream:
        if line.strip():
            yield line.rstrip('
')

with open('input.txt', encoding='utf-8') as stream:
    for line in nonempty_lines(stream):
        if line == 'STOP':
            break
# with가 파일 종료를 책임짐
```

`input.txt`는 독자가 준비할 예시 파일이며 이 코드 조각의 실행 결과를 저장한 것은 아닙니다. generator 안에서 파일을 열고 yield하면 consumer가 중간에 멈췄을 때 close/종료를 누가 책임지는지도 정해야 합니다. 참조 해제/GC 시점에만 의존하지 않습니다.

## 4. context manager의 계약

with는 시작·종료 경계를 표현합니다. 파일을 닫거나 lock을 반환하거나 transaction을 commit/rollback할 수 있지만 구체 의미는 해당 객체의 계약입니다. 모든 with가 예외를 숨기거나 rollback하는 것은 아닙니다. `__exit__`의 반환값은 예외 전파에 영향을 줍니다.

async context manager는 await가 필요한 진입/정리를 표현합니다. 취소·정리 실패가 있으므로 수명 상한과 로그/오류 처리를 설계합니다.7-4의 취소가 이 문제와 연결됩니다.

## 5. 마법의 경계

decorator·descriptor·동적 attribute가 공통 정책을 줄일 수 있지만 호출 위치·타입·오류가 숨겨지면 디버깅 비용이 큽니다. 반복이 실제로 있고 계약을 명확히 설명할 수 있을 때 사용합니다. 평범한 함수·명시적 객체로 충분한지 먼저 비교합니다.

## 6. 적용 과제

수백만줄CSV를 읽어 필터링하되 중간에 중단될 수 있는 작업에서 list·generator·with의 수명을 설계하세요. 여러 번 집계해야 하면 다시 읽기·작은 집계상태·materialize 중 무엇을 선택할지도 적습니다.

## 퀴즈

### Q1

generator는 여러 번 list로 바꿔도 같은 결과를 계속 주는가?

### Q2

with를 쓰면 모든 예외가 자동으로 사라지는가?

### Q3

list와 generator의 메모리·오류 시점을 비교하라.

### Q4

파일을 잡은 generator를 중간 중단할 때 중요한 설계는?

### Q5

큰 CSV의 중단 가능한 처리와 두 번 집계 요구에 자료구조·수명을 선택하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [PEP20](https://peps.python.org/pep-0020/), [Python contextlib](https://docs.python.org/3/library/contextlib.html) — 원칙과 수명 계약 참고.
- 이 편의 짧은 코드 조각은 설명용이며 독자 파일의 실제 처리 검증은 아닙니다.

확인일: 2026-10-02. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
