# 10-1. pytest의 기본 단위

[목차](../README.md) · [정답·해설](01-pytest-answers.md)

예상 55분. 목표: 업무 규칙을 기대값으로 표현하고, fixture와 parametrize로 독립적인 사례를 만듭니다.

## 1. 실행할 예제

[예제 폴더](../labs/testing_demo/), [가격 규칙](../labs/testing_demo/pricing.py), [테스트](../labs/testing_demo/test_pricing.py), [의존성](../labs/requirements-testing.txt).

규칙: 금액은 정수 cent, 할인은 basis point(100bp=1%), 할인 후 금액을 내림, 할인 후 10,000cent 이상이면 배송비 0, 미만이면 599cent입니다. 실제 결제 API가 아니라 테스트용 견적 규칙입니다. 운영 주문의 가격은 서버의 신뢰한 원본에서 결정해야 합니다.

```bash
python3 -m venv /tmp/study-tests
/tmp/study-tests/bin/python -m pip install -r study/labs/requirements-testing.txt
cd study/labs/testing_demo
/tmp/study-tests/bin/python -m pytest -q -c pytest.ini
```

실제 검증은 별도 `/workspace/study-python` 환경에서 pytest 8.3.5로 수행했습니다. **21개 테스트 통과**입니다. pytest 수집 개수와 실행 결과를 함께 확인하세요. 0개 수집은 기능 검증 성공이 아닙니다.

## 2. assert가 말해야 하는 것

`assert result`만 있으면 non-empty dict인지 정도만 확인할 수 있습니다. 배송비 0, 합계 10000 같은 사용자에게 중요한 결과를 구체적으로 검사합니다. 기대값을 본문 함수와 똑같은 계산식으로 다시 만들면 같은 실수를 두 번 적을 수 있으므로 작은 사례는 수동 계산한 값이 유용합니다.

```python
@pytest.mark.parametrize('price,fee', [(9999,599), (10000,0), (10001,0)])
def test_boundary(line_factory, price, fee):
    result = quote([line_factory(unit_cents=price)])
    assert result['shipping_cents'] == fee
```

위는 실제 테스트를 줄인 발췌입니다. 경계 바로 아래·같음·바로 위를 구분합니다.

## 3. fixture와 parametrize

fixture는 준비와 정리를 테스트 수명에 연결합니다. fixture를 사용한다고 모든 상태가 자동 격리되는 것은 아닙니다. scope를 넓히면 준비 비용은 줄지만 변하는 DB/객체를 공유할 위험이 있습니다.

parametrize는 같은 규칙을 다른 입력으로 독립 수집합니다. 긴 for 루프 하나는 첫 실패에서 나머지를 확인하지 못하고 사례별 이름을 잃기 쉽습니다. 각 사례의 의미가 다르면 억지로 하나의 거대한 파라미터 표에 넣기보다 별도 테스트가 낫습니다.

## 4. 예외와 경계

예제는 빈 주문·잘못된 할인·수량·단가를 ValueError로 거부합니다. Python bool은 int의 하위 타입이므로 단순 isinstance(x,int)만으로는 금액/수량 정책과 다를 수 있습니다. 명시적 업무 규칙과 테스트를 둡니다.

예외가 났다는 것만 보는 것보다 예상 예외 종류와 필요한 메시지·상태를 검사합니다. 내부 구현 문구 전체에 지나치게 결합하면 리팩토링 비용이 커지므로 공개 계약과 내부 표현을 구분합니다.

## 5. 적용 과제

무료배송 기준이 ‘할인 전’에서 ‘할인 후’로 바뀌는 경우 어떤 테스트가 변해야 하는지 설명하세요. 정상·경계·오류와 입력 객체가 바뀌지 않는 성질을 각각 검사합니다.

## 퀴즈

### Q1

pytest가 0개 테스트를 수집해 종료하면 기능이 검증되었는가?

### Q2

assert result만으로 배송비가 맞는지 알 수 있는가?

### Q3

9999·10000·10001 세 사례를 두는 이유는?

### Q4

fixture scope를 넓히는 이익과 비용은?

### Q5

할인 후 무료배송 규칙의 경계·오류·부수효과 테스트를 설계하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [pytest fixture](https://docs.pytest.org/en/stable/how-to/fixtures.html), [parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html) — 도구 참고.
- 본문의 실행 증거는 21개 통과와 10-6의 coverage·mutation 결과입니다.

확인일: 2026-10-02. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
