# 5-6. PostgreSQL 두 세션 격리·락·재시도 실습

[목차](../README.md) · [정답·해설](06-isolation-lab-answers.md)

예상 75분. 목표: transaction 순서를 직접 통제하여 스냅샷·write skew·락 대기를 구분합니다.

## 1. 환경과 범위

[실행 코드](../labs/postgres_isolation.py), [원본 JSON](../results/postgres-2026-10-01.json), [Python 의존성](../labs/requirements-postgres.txt).

2026-10-01 실행: CPython 3.12.14, psycopg 3.2.10, PostgreSQL 17.6 (Debian), Docker `postgres:17.6-bookworm`, 이미지 digest `sha256:f3bd19c606e442c3d7bdfa8002e03fe260a1023351e0ea4598032022b68dd6e3`. 컨테이너 CPU 1, 메모리 512MiB, loopback 포트와 임시 데이터 디렉터리를 사용했습니다. 아래 버전은 재현용이며 최신 운영 권장 버전이라는 뜻은 아닙니다.

실행기는 독립된 DB 연결 A·B를 열고 명령을 교차 실행합니다. 스레드를 동시에 달리지 않아도 transaction 수명이 겹치면 동시성 이상을 재현할 수 있습니다. sleep으로 우연한 타이밍을 기다리지 않습니다.

## 2. 재현 명령

Docker와 Python 가상환경이 필요합니다. 아래 인증 생략 설정은 **임시 학습용 loopback DB**에만 사용합니다. 같은 머신의 다른 프로세스도 접근할 수 있으므로 실제 데이터나 공유 운영 환경에 사용하지 마세요. 별도 외부 DB 접속 문자열을 받지 않는 실행기입니다.

```bash
python3 -m venv /tmp/study-pg-venv
/tmp/study-pg-venv/bin/python -m pip install -r study/labs/requirements-postgres.txt

docker_local() {
  env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS     -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH     docker --host=unix:///var/run/docker.sock "$@"
}
docker_local run -d --name study-pg-lab --cpus=1 --memory=512m   --publish 127.0.0.1::5432 --env POSTGRES_HOST_AUTH_METHOD=trust   --env POSTGRES_DB=study --tmpfs /var/lib/postgresql/data   postgres:17.6-bookworm
docker_local exec study-pg-lab pg_isready -U postgres -d study
docker_local port study-pg-lab 5432/tcp
```

`pg_isready`가 아직 실패하면 초기화 로그를 확인하고 준비 후 진행합니다. 출력된 포트로 다음 `32769`를 바꾸세요. 기존 컨테이너 이름이 있다면 다른 이름을 사용하고 해당 이름을 끝까지 일관되게 적용합니다.

```bash
/tmp/study-pg-venv/bin/python study/labs/postgres_isolation.py   --port 32769 --output /tmp/postgres-new.json
docker_local rm -f study-pg-lab
```

실제 검증은 `/workspace/study-python` 가상환경과 `study-postgres-20261001` 컨테이너에서 수행했습니다. 위 명령은 동일 패키지·이미지를 재현하기 위한 독자용 경로입니다. 실패해도 자신이 만든 컨테이너를 마지막에 정리하세요. 실제 검증용 컨테이너는 이미 제거했습니다.

## 3. 실제 결과

| 시나리오 | 실행 순서의 핵심 | 관찰·검증 |
| --- | --- | --- |
| Read Committed 재조회 | A 읽기, B 수정 commit, A 읽기 | 100 → 200 |
| Repeatable Read 재조회 | 같은 순서 | 100 → 100 |
| 오래된 읽기값 덮어쓰기 | A/B 각각 100, A 101 commit, B 101 commit | 최종 101 |
| DB 원자적 증가 | UPDATE value=value+1 두 번 | 최종 102 |
| Repeatable Read write skew | A/B 모두 당직자 2명 확인, 각자 자기 행 false | 둘 다 commit, 0명 |
| Serializable write skew | 같은 읽기·쓰기 순서 | B commit 40001, 1명 유지 |
| 락 대기 제한 | A FOR UPDATE, B 같은 행 UPDATE | B 55P03 |

두 증가 SQL은 순차 실행한 대조군입니다. 높은 병행 부하의 성능 실험은 아닙니다. 원자적 증가가 반환하는 값을 통해 앱의 오래된 상수 덮어쓰기와 차이를 확인합니다.

Serializable 실패 후 B는 새 transaction에서 당직자 수를 **다시 읽고**, 1명이므로 퇴근하지 않기로 판단합니다. 실패한 UPDATE만 다시 실행했다면 업무 조건을 다시 평가하지 못합니다.

## 4. 직접 따라 적을 SQL 순서

```sql
-- A와 B 각각 별도 세션에서:
BEGIN ISOLATION LEVEL REPEATABLE READ;
SELECT count(*) FROM doctors WHERE on_call;
-- 두 세션 모두 2를 읽은 후
-- A:
UPDATE doctors SET on_call=false WHERE id=1;
-- B:
UPDATE doctors SET on_call=false WHERE id=2;
-- A COMMIT, 이어 B COMMIT
```

이 코드는 개념 설명용이며 실행기가 만든 임시 스키마는 실행 종료 시 제거됩니다. 수동 실습을 하려면 자신만의 스키마와 doctors 테이블부터 준비하세요. 운영 테이블에 실행하지 않습니다.

## 5. 락 타임아웃과 재시도

55P03은 이 실습에서는 100ms `lock_timeout`으로 발생했습니다. 같은 SQLSTATE만으로 모든 장애 원인을 단정하지 말고 DB 오류 메시지·문장·설정을 함께 봅니다. `statement_timeout=5s`는 개별 문장의 전체 시간 제한이고 lock_timeout은 락 획득 대기 제한입니다.

40001 재시도는 전체 transaction 단위, 제한된 횟수와 deadline, 충돌 완화를 위한 지연을 고려합니다. 결제 등 외부 부작용이 transaction 함수 안에 있으면 무조건 반복해서는 안 됩니다. SQLSTATE 40P01 deadlock은 별도 현상이며 이 실험에서 재현하지 않았습니다.

## 6. 적용 과제

A/B를 바꾼 순서, 세 번째 당직자 추가, 실패 재시도 횟수 제한을 설계해 보세요. 각 변경 전에 예상 결과를 적고 나중에 비교합니다. 이 확장 과제는 실행한 결과에 포함하지 않았습니다.

## 퀴즈

### Q1

CPU에서 SQL이 정확히 같은 순간 실행되어야 동시성 이상을 실험할 수 있는가?

### Q2

Serializable 실험에서 실패한 세션이 받은 SQLSTATE는?

### Q3

Repeatable Read에서 두 당직자가 모두 퇴근할 수 있었던 이유는?

### Q4

lock_timeout과 statement_timeout의 차이는?

### Q5

40001 재시도 함수를 설계하라. 재시도 범위·종료 조건·외부 부작용을 포함하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [PostgreSQL 17 격리 수준](https://www.postgresql.org/docs/17/transaction-iso.html).
- [오류 코드](https://www.postgresql.org/docs/17/errcodes-appendix.html).
- 원본 결과에는 검증한 7개 격리·락 사례와 인덱스 전후 계획을 보존했습니다. 스키마 제거와 연결 종료도 확인했습니다.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
