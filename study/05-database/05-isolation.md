# 5-5. 격리 수준과 동시성 이상

[목차](../README.md) · [정답·해설](05-isolation-answers.md)

예상 60분. 목표: 두 transaction의 실행 순서를 따라 이상 현상을 판별하고, 격리 이름과 DB 구현을 구분합니다.

## 1. 같은 transaction인데 값이 달라진다

```text
A: BEGIN; 잔액 조회 → 100
B: 잔액을 200으로 수정; COMMIT
A: 같은 잔액 재조회 → ?
```

PostgreSQL Read Committed의 일반 SELECT는 문장 시작 시점의 스냅샷을 보므로 두 번째 값이 200일 수 있습니다. Repeatable Read는 transaction의 첫 실제 질의/변경 시점에 정한 스냅샷을 유지하므로 100을 볼 수 있습니다. 자신이 변경한 값은 별도로 보입니다. 모든 transaction이 BEGIN 직후 동일한 시점의 스냅샷을 잡는다고 단순화하지 마세요.

## 2. 이상 현상 구분

| 현상 | 무엇이 달라지는가 | 예 |
| --- | --- | --- |
| Dirty read | 아직 commit되지 않은 타 transaction 값 | 나중에 rollback될 잔액 읽음 |
| Non-repeatable read | 같은 행 재조회 값 | 100을 읽고 나중에 200 읽음 |
| Phantom read | 같은 조건의 행 집합 | 열린 주문 3개가 재조회 시 4개 |
| Lost update | 오래된 읽기 기반 덮어쓰기 | 둘 다 100 읽고 각각 101 저장, 증가 하나 소실 |
| Write skew | 서로 다른 행을 바꿔 공통 불변식 위반 | 당직자 둘이 모두 상대가 남는다고 판단하고 퇴근 |

lost update와 write skew는 dirty read가 없어도 발생할 수 있습니다. 하나의 행에 atomic increment를 쓰는 대책이 여러 행에 걸친 ‘적어도 한 명 당직’ 조건을 자동 해결하지는 않습니다.

## 3. 표준 수준과 PostgreSQL 구현

| PostgreSQL 17 수준 | 일반적인 관찰 | 주의 |
| --- | --- | --- |
| Read Uncommitted | Read Committed와 동일 동작 | 더러운 읽기를 허용하는 별도 구현이 아님 |
| Read Committed | 문장별 스냅샷 | 문장 사이 값·행 집합 변경 가능 |
| Repeatable Read | transaction 스냅샷 | phantom도 방지하지만 write skew 가능 |
| Serializable | 성공한 transaction 집합에 직렬 실행과 동등한 결과 | 충돌 시 40001 실패, 전체 재시도 필요 |

SQL 표준의 Repeatable Read가 phantom을 허용할 수 있다는 최소 보장과 PostgreSQL 구현이 더 강하게 방지한다는 사실을 구분합니다. MySQL InnoDB도 같은 이름을 제공하지만 consistent read·locking read·gap/next-key lock 등 구체 동작이 다릅니다. 여기의 표를 다른 DB에 그대로 복사하지 마세요.

## 4. 잠금과 MVCC

MVCC는 여러 행 버전을 이용해 독자가 자기 스냅샷을 읽도록 합니다. 읽기와 쓰기의 충돌을 줄이지만 쓰기끼리의 락과 불변식 검증을 없애지 않습니다. `SELECT ... FOR UPDATE`는 읽은 행을 잠가 같은 행의 변경을 조정합니다. 하지만 현재 결과가 빈 집합인 조건에서 미래에 생길 행까지 항상 잠근다는 뜻은 아닙니다.

Read Committed의 `UPDATE value=value+1`은 같은 행에 대한 원자적 갱신으로 오래된 앱 값 덮어쓰기 문제를 피할 수 있습니다. 반대로 SELECT 100 후 앱에서 계산한 101을 저장하면 다른 transaction의 증가를 덮어쓸 수 있습니다. 복잡한 조건은 version 컬럼을 사용한 조건부 UPDATE와 영향 행 수 확인도 대안입니다.

## 5. 선택 비용

| 전략 | 이익 | 비용 |
| --- | --- | --- |
| 원자적 SQL·제약 | DB에서 작은 규칙 강제 | 복잡한 다중 행 규칙 표현 한계 |
| 명시적 잠금 | 충돌 작업의 순서 제어 | 대기·deadlock·잠금 범위 설계 |
| 낙관적 version 비교 | 충돌 없는 경우 대기 감소 | 충돌 응답·전체 업무 재시도 |
| Serializable | 복잡한 읽기-쓰기 관계의 직렬성 | 추적 비용·serialization failure·재시도 |

Serializable이 사용자 입력이나 외부 시스템까지 직렬화하는 것은 아닙니다. 한 불변식을 지키는 관련 transaction들이 같은 프로토콜을 따라야 합니다. 예외 경로가 잠금/제약 없이 쓰면 보장이 깨질 수 있습니다.

## 6. 적용 과제

‘당직자는 최소 한 명’에서 두 사람이 각각 상대를 확인하고 자기 행만 false로 바꾸는 순서를 적으세요. 다음 편에서 Repeatable Read의 두 commit과 Serializable의 실패를 실제 두 세션으로 비교합니다.

## 퀴즈

### Q1

PostgreSQL Read Uncommitted로 dirty read를 재현할 수 있는가?

### Q2

PostgreSQL Repeatable Read에서 phantom이 방지되면 모든 직렬성 문제가 해결되는가?

### Q3

Lost update와 write skew를 행 범위·불변식 관점으로 구분하라.

### Q4

40001을 받으면 마지막 UPDATE만 재실행해도 되는가? 이유는?

### Q5

당직자 최소 한 명 조건을 지키는 두 설계와 각각의 비용을 제시하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [PostgreSQL 17 Transaction Isolation](https://www.postgresql.org/docs/17/transaction-iso.html) — 수준별 보장, Repeatable Read의 추가 보장, 재시도 단위.
- [MySQL InnoDB 격리 수준](https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html) — 다른 구현 비교를 위한 후속 읽기. MySQL 실험은 수행하지 않았습니다.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
