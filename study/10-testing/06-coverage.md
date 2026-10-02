# 10-6. 커버리지와 회귀 방지

[목차](../README.md) · [정답·해설](06-coverage-answers.md)

예상 60분. 목표: 실행한 줄·분기와 검증한 동작을 구분하고, 실제 결함을 잡는 assertion인지 확인합니다.

## 1. 커버리지가 알려 주는 것

문장 coverage는 실행된 코드 줄, branch coverage는 조건의 갈래를 얼마나 거쳤는지 보여 줍니다. 어느 쪽도 기대값이 올바르다는 증거는 아닙니다. 테스트가 함수를 호출만 하고 아무 결과도 검사하지 않아도 coverage는 높을 수 있습니다.

죽은 코드·예외·상태 전이 누락을 찾는 지도처럼 사용합니다. 수치 목표 때문에 의미 없는 테스트나 과도한 mock을 만들지 않습니다.

## 2. 실제 실행

```bash
cd study/labs/testing_demo
COVERAGE_FILE=/tmp/study-tests.coverage /workspace/study-python/bin/python -m pytest   -q -c pytest.ini --cov=pricing --cov=quote_api --cov-branch   --cov-report=term-missing --cov-report=json:/tmp/coverage-new.json
```

`/workspace/study-python`은 검증에 사용한 환경입니다. 독자 환경에서는 설치한 venv의 python 경로로 바꾸세요. [원본 coverage](../results/testing-coverage-2026-10-02.json).

| 모듈 | 문장 | 누락 문장 | 분기 | 부분 분기 | 도구 표시 coverage |
| --- | --- | --- | --- | --- | --- |
| pricing.py | 20 | 0 | 10 | 0 | 100% |
| quote_api.py | 13 | 0 | 2 | 1 | 93% |
| 전체 | 33 | 0 | 12 | 1 | 98% |

pytest 8.3.5, pytest-asyncio0.25.3, pytest-cov6.0.0, coverage7.16.2에서 **21 passed**. 문장 커버리지는 모두 실행되었지만 앱 ready가 false일 때의 예외 갈래는 검증하지 않았습니다. 표의 마지막 열은 문장+분기를 고려한 도구 표시값이며 순수 문장 coverage와 다릅니다.

## 3. 의도적인 결함으로 assertion 검사

[mutation 검사 코드](../labs/check_test_mutation.py)는 임시 복사본의 `discounted >= 10000`을 `discounted > 10000`으로 바꿉니다. 원본 파일은 수정하지 않고 검사 후 임시 디렉터리를 제거합니다.

```bash
/workspace/study-python/bin/python study/labs/check_test_mutation.py   --output /tmp/mutation-new.json
```

이 명령은 저장소 루트에서 실행합니다. [실제 결과](../results/testing-mutation-2026-10-02.json)는 **예상대로 3 failed, 18 passed**, pytest exit code1이었습니다. 무료배송 경계·다중 품목 합계·API 계약 테스트가 오류를 잡았습니다. 검사 실행기는 이 예상 실패를 확인했으므로 종료코드0입니다. 정상 suite의 실패로 보고하지 않습니다.

## 4. 무엇을 더 보아야 할까

한 변이를 잡았다고 모든 버그를 잡는 것은 아닙니다. 할인 반올림·빈 주문·권한·동시성·외부 장애 등 다른 규칙에는 다른 테스트가 필요합니다. mutation testing은 test sensitivity를 점검하는 방법이며 동일 동작을 만드는 변이·비용·오탐 해석도 있습니다.

회귀 테스트는 실제 실패 조건을 최소한으로 재현하고, 수정 전에는 실패하며 수정 후에는 통과하는 것을 확인할 때 강한 증거가 됩니다. 구현 내부 구조가 아니라 유지해야 할 계약을 중심으로 만듭니다.

## 5. 적용 과제

‘할인 전 금액으로 배송비 판단’ 변이를 임시 복사본에 넣으면 어떤 테스트가 실패해야 하는지 예측하세요. 이 추가 변이는 실행하지 않았습니다. coverage 수치가 같아도 assertion 결과는 달라질 수 있음을 설명하세요.

## 퀴즈

### Q1

100% coverage이면 요구사항이 모두 맞는가?

### Q2

이번 정상 테스트와 변이 테스트의 결과를 구분하라.

### Q3

문장 coverage와 branch coverage 차이는?

### Q4

왜 원본이 아니라 임시 복사본에 변이를 넣었는가?

### Q5

실제 발견한 무료배송 오류의 회귀 방지를 어떤 증거로 검증할 것인가?

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [coverage.py branch coverage](https://coverage.readthedocs.io/en/latest/branch.html) — 도구 참고.
- 실행한 coverage와 변이 원본 JSON을 함께 보존했습니다. 테스트 범위는 교육용 가격/견적 예제입니다.

확인일: 2026-10-02. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
