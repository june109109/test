# 5-4. 트랜잭션과 ACID

[목차](../README.md) · [정답·해설](04-transactions-answers.md)

예상 50분. 목표: DB 원자성의 경계를 설명하고, 외부 결제 실패·성공 여부 불명 상황을 설계합니다.

## 1. 계좌 이체의 두 UPDATE

A 잔액에서 100을 차감했는데 B 잔액 증가가 실패하면 돈이 사라집니다. 둘을 하나의 transaction에 묶으면 commit 또는 rollback으로 묶음의 성공을 결정할 수 있습니다. 단, 잔액 검사와 동시 요청 처리까지 올바르려면 제약·격리·잠금 전략이 필요합니다.

```sql
BEGIN;
UPDATE accounts SET balance = balance - 100
WHERE id = 1 AND balance >= 100;
-- 앱은 영향받은 행이 정확히 1개인지 확인. 아니면 ROLLBACK.
UPDATE accounts SET balance = balance + 100 WHERE id = 2;
-- 받는 계좌가 없을 때도 ROLLBACK하도록 확인.
COMMIT;
```

이것은 제어 흐름을 설명하는 부분 예제이며 주석이 자동 검증을 수행하지 않습니다. 여러 계좌 잠금이 필요한 경우 일관된 잠금 순서로 deadlock 가능성을 줄이고 실패 시 재시도 정책을 둡니다.

## 2. ACID를 기능 이름으로 풀기

| 성질 | 뜻 | 자동으로 해결되지 않는 것 |
| --- | --- | --- |
| Atomicity | 묶인 DB 변경의 전부 적용/취소 | 외부 HTTP 결제까지 취소 |
| Consistency | 선언한 제약과 올바른 transaction이 불변식 유지 | 애초에 잘못 정의한 업무 규칙 |
| Isolation | 동시 실행의 관찰·충돌 규칙 | 모든 수준에서 직렬 실행 보장 |
| Durability | 성공한 commit의 지속성 보장 | 모든 복제본 즉시 반영·백업·무손실 failover |

Durability는 DB의 WAL·동기화 설정·저장장치와 장애 모델에 의존합니다. PostgreSQL의 `synchronous_commit=off`처럼 지연을 줄이는 설정은 장애 시 최근 commit 손실 가능성을 바꿉니다. 이 편에서 그 설정 변경을 권하거나 장애 복구를 시험한 것은 아닙니다.

## 3. commit 응답이 사라지면

서버가 commit을 완료한 뒤 네트워크가 끊어지면 클라이언트는 실패처럼 보지만 데이터는 반영되어 있을 수 있습니다. 타임아웃은 미실행의 증거가 아닙니다. 사용자 요청 ID에 unique 제약을 두고 같은 요청의 상태를 조회하거나 멱등 처리하는 설계가 필요합니다.

rollback도 이미 보낸 이메일·외부 결제·S3 업로드를 되돌리지 않습니다. 외부 연동에는 outbox, 상태 머신, 멱등 키, 보상 작업 같은 별도 설계가 필요합니다. 보상은 과거 일이 없었던 것처럼 완전 복원한다는 뜻이 아니라 환불 등 업무적으로 대응하는 동작입니다.

## 4. transaction을 짧게 유지하는 이유

DB 연결과 락을 쥔 채 외부 API를 30초 기다리면 DB 동시성·풀 용량·실패 영향이 커집니다. 긴 transaction은 MVCC의 오래된 버전 정리에도 영향을 줄 수 있습니다.

외부 호출을 무작정 transaction 밖으로 옮기는 것만으로 원자성이 유지되지는 않습니다. ‘결제대기 주문 기록 → 멱등 키로 결제 → 성공/실패 상태 반영’ 같은 단계와 복구 담당자를 명확하게 정의합니다. 더 단순한 DB 내부 작업은 하나의 짧은 transaction으로 끝내는 것이 좋습니다.

## 5. savepoint와 autocommit

savepoint는 transaction 안의 일부 작업을 되돌릴 지점입니다. 바깥 transaction이 rollback되면 savepoint 이전 변경도 함께 취소됩니다. 내부 COMMIT과 같은 기능이 아닙니다.

드라이버의 autocommit과 암묵적 BEGIN 규칙을 확인하세요. SELECT 한 번이 transaction을 열고 앱이 idle 상태로 오래 유지할 수 있습니다. Python context manager의 정상/예외 종료 동작도 드라이버마다 구체적으로 확인해야 합니다.

## 6. 적용 과제

결제 요청이 타임아웃된 주문을 곧바로 재결제할지 결정해 보세요. 같은 멱등 키, 결제 제공자 상태 조회, 주문 상태 전이, 재시도 상한, 운영자가 확인할 기록을 그리세요. ‘DB rollback이 모든 것을 취소한다’는 전제는 사용할 수 없습니다.

## 퀴즈

### Q1

DB rollback으로 외부 이메일 발송도 취소되는가?

### Q2

commit 호출의 타임아웃은 DB 변경 실패를 확정하는가?

### Q3

ACID의 consistency와 isolation을 구분하라.

### Q4

DB transaction 안에서 느린 외부 호출을 기다릴 때 비용 두 가지는?

### Q5

결제 요청 결과가 불명확할 때 중복 결제를 피하고 복구하는 흐름을 설계하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [PostgreSQL transaction 입문](https://www.postgresql.org/docs/17/tutorial-transactions.html) — all-or-nothing, commit/rollback, savepoint.
- [PostgreSQL WAL 설정](https://www.postgresql.org/docs/17/runtime-config-wal.html) — durability의 구체적 설정 참고.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
