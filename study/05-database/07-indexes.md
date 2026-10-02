# 5-7. 인덱스와 실행계획

[목차](../README.md) · [정답·해설](07-indexes-answers.md)

예상 65분. 목표: 질의 조건·정렬·분포에 맞게 인덱스를 제안하고, EXPLAIN의 추정과 관찰을 구분합니다.

## 1. 목차를 만들면 모든 읽기가 빨라질까

인덱스는 질의를 빠르게 찾기 위한 추가 자료구조입니다. 대신 쓰기 때 인덱스도 갱신하고 저장 공간·메모리·WAL을 사용합니다. 하나의 테이블에 가능한 모든 인덱스를 만드는 것은 읽기 이익과 쓰기 비용을 함께 증가시킵니다.

B+트리 개념에서는 내부 노드가 탐색을 안내하고 정렬된 리프가 키와 행 위치 정보를 담아 범위 탐색을 돕습니다. 높은 분기수로 적은 페이지 접근을 목표로 합니다. PostgreSQL 문서의 B-tree는 이 계열의 구현이며 제품마다 리프·페이지·행 저장 방식이 다릅니다. InnoDB의 clustered primary key 구조를 PostgreSQL heap 구조와 같게 설명하지 않습니다.

## 2. 카디널리티와 선택도

컬럼의 distinct 값 수를 카디널리티라 부르는 문맥과 실행계획의 예상 행 수를 카디널리티라 부르는 문맥을 구분하세요. 선택도도 문헌에 따라 비율의 방향을 다르게 표현하므로 여기서는 ‘전체 중 조건에 걸리는 비율’을 직접 적습니다.

status가 두 종류여도 failed가 0.1%라면 `WHERE status='failed'`는 좁은 집합을 찾습니다. 반대로 유일한 ID 컬럼이라도 `WHERE id>0`이 거의 전부를 반환하면 인덱스가 이득이 아닐 수 있습니다. distinct 값 수뿐 아니라 **특정 값의 분포와 질의 범위**가 중요합니다. partial index도 대안이지만 질의 조건이 인덱스 조건을 만족해야 합니다.

## 3. 복합 인덱스의 순서

```sql
SELECT id, created_at FROM orders
WHERE user_id = 42
ORDER BY created_at DESC LIMIT 20;

CREATE INDEX orders_user_time ON orders(user_id, created_at DESC);
```

동일 user_id 구간을 찾아 최신 순으로 조금만 읽을 수 있습니다. `(created_at, user_id)`는 같은 질의에서 다른 탐색 비용을 갖습니다. 모든 경우에 ‘카디널리티 높은 컬럼부터’라는 규칙을 쓰지 말고 equality·range·정렬·다른 질의를 함께 봅니다.

PostgreSQL 17의 다중 컬럼 B-tree는 선두 equality 조건과 그 다음 첫 inequality가 탐색 범위를 줄이는 데 중요합니다. 선두 조건이 없으면 ‘절대 사용 불가’는 아니지만 많은 인덱스 항목을 스캔할 수 있습니다. 다른 버전의 skip scan 같은 기능과 혼동하지 않습니다.

INCLUDE로 반환 컬럼을 담는 covering 전략은 heap 접근을 줄일 기회를 주지만 인덱스가 커집니다. PostgreSQL index-only scan도 MVCC 가시성 확인 때문에 heap fetch가 생길 수 있습니다.

## 4. EXPLAIN 읽기

`EXPLAIN`은 계획과 추정치를 보여 줍니다. `EXPLAIN ANALYZE`는 **실제로 문장을 실행**하여 시간·행 수를 수집합니다. UPDATE/DELETE도 실제 변경하므로 학습용 데이터에서 수행합니다.

- cost는 밀리초가 아닌 플래너의 비용 단위입니다.
- estimated rows와 actual rows가 크게 다르면 분포·통계·상관관계를 점검합니다.
- actual rows/time은 loops와 함께 읽습니다. 상위 노드가 하위 작업을 포함하므로 단순 합산하지 않습니다.
- Seq Scan이 항상 실패는 아닙니다. 작은 테이블이나 많은 행을 반환하면 유리합니다.
- shared hit는 DB 버퍼에서 찾은 접근, shared read는 버퍼로 읽어온 블록입니다. OS 캐시에 있을 수 있으므로 디스크 물리 I/O와 일대일 대응하지 않습니다.

## 5. 실제 10만 행 실험

[실습 코드](../labs/postgres_isolation.py), [원본 계획 JSON](../results/postgres-2026-10-01.json). 실행 방법은 [5-6](06-isolation-lab.md)에 있습니다. 데이터는 user_id 1,000종에 균등 분포, 해당 사용자의 100행 중 최신 20행 조회입니다. created_at은 순서를 나타내는 정수로 단순화했습니다.

| 항목 | 인덱스 전 | 복합 인덱스 후 |
| --- | --- | --- |
| 계획 | Seq Scan → Sort → Limit | Index Scan → Limit |
| Seq Scan 필터 탈락 | 99,900행 | 해당 노드 없음 |
| 반환 | 20행 | 20행 |
| 실행 시간 | 5.007ms | 0.041ms |
| 최상위 shared hit / read blocks | 1600 / 0 | 20 / 2 |

한 번의 로컬 실행 결과입니다. 캐시 상태·작은 데이터·계측 비용 때문에 ‘항상 122배 빠름’ 같은 결론은 내릴 수 없습니다. 이번에 확인한 핵심은 **계획의 구조와 읽는 범위의 변화**입니다. 인덱스 쓰기 비용·다양한 사용자 분포·동시 부하·인덱스 생성 잠금은 측정하지 않았습니다.

## 6. 적용 과제

실패 주문이 드물고 운영자는 최근 실패 주문 50개를 본다고 합시다. 일반 `(status,created_at)`과 `WHERE status='failed'` 부분 인덱스를 비교하세요. 성공 주문 검색, 상태 변경 비용, prepared query 조건에 따른 계획 가능성도 적습니다.

## 퀴즈

### Q1

EXPLAIN ANALYZE는 질의를 실제 실행하는가?

### Q2

boolean 컬럼 인덱스는 항상 무용한가?

### Q3

WHERE user_id=? ORDER BY created_at DESC LIMIT 20에 제안할 인덱스와 이유는?

### Q4

계획 cost와 실행 시간, shared read와 물리 디스크 I/O를 구분하라.

### Q5

느린 질의에 인덱스를 추가하기 전후 어떤 증거와 비용을 확인할 것인가?

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [PostgreSQL 다중 컬럼 인덱스](https://www.postgresql.org/docs/17/indexes-multicolumn.html).
- [EXPLAIN 사용](https://www.postgresql.org/docs/17/using-explain.html).
- [부분 인덱스](https://www.postgresql.org/docs/17/indexes-partial.html) — 확장 과제의 참고 문서.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
