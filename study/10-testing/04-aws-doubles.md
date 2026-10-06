# 10-4. AWS 대역과 호환 환경

[목차](../README.md) · [정답·해설](04-aws-doubles-answers.md)

예상 50분. 목표: mock·moto·LocalStack·실제 sandbox의 검증 범위와 비용을 구분합니다.

## 1. mock 성공이 운영 성공이 아닌 이유

mock은 내가 기대한 응답을 직접 반환하도록 만들 수 있습니다. 실제 SDK 인자·HTTP 직렬화·IAM·region·서비스 제한이 틀려도 mock이 허용하면 테스트는 통과합니다. mock 자체가 나쁜 것이 아니라 검증한 경계가 제한적입니다.

| 대역 | 강점 | 빠지는 대표 범위 |
| --- | --- | --- |
| 함수 mock/stub | 분기·오류·재시도 빠른 제어 | 실제 SDK/네트워크/서비스 계약 |
| botocore Stubber | 기대 SDK 호출·응답 스키마 검사 | 실제 HTTP·IAM·서버 동작 |
| moto | AWS API의 메모리 모사로 업무 흐름 | 서비스/기능별 구현 차이 |
| LocalStack | 로컬 endpoint로 SDK/네트워크 경계 | 실제 AWS의 권한·확장·운영 특성 |
| 실제 sandbox 계정 | 실제 서비스 계약·IAM 확인 | 비용·격리·정리·시간·권한 필요 |

제품의 지원 범위와 버전은 변합니다. ‘AWS를 완전히 동일하게 재현’한다고 가정하지 않습니다.

## 2. 무엇을 mock할까

가격 계산의 테스트에서는 S3가 필요 없을 수 있습니다. 파일 저장 어댑터 테스트에서는 get/put 계약·body close·오류 매핑을 검사합니다. 통합 테스트에서는 실제 SDK를 LocalStack endpoint에 연결해 serialization·연결·객체 내용을 검증합니다.

구현 내부의 helper 호출 횟수를 과도하게 검사하면 리팩토링마다 깨집니다. 대신 외부 계약과 중요 부작용을 검사하세요. 재시도 정책처럼 횟수가 업무상 중요하면 호출 횟수 검사가 의미 있습니다.

## 3. 모의 응답의 소유권

S3 `get_object`의 Body는 읽기·종료 수명을 가진 stream입니다. 단순 bytes 하나로 대체하면 close 누락을 발견하지 못할 수 있습니다. 실패 중간의 부분 읽기·timeout·NoSuchKey 등 실제 소비자가 처리해야 하는 계약을 모사합니다.

모든 예외를 Exception 하나로 바꾸면 SDK 오류 code·HTTP status에 따른 분기 문제가 사라져 보일 수 있습니다. 필요한 오류 형태를 제공자 계약에 맞춥니다.

## 4. 실제 수행 범위

4-4에서는 boto3 1.35.99와 LocalStack 4.0.0으로 실제 로컬 HTTP S3 읽기 180회와 내용·body 종료·버킷 정리를 확인했습니다. 이는 실제 AWS IAM·리전·대용량 multipart·운영 latency 검증이 아닙니다. moto·Stubber는 이번 자료에서 설명만 했으며 실행하지 않았습니다.

독자 확장에서는 같은 저장소 계약 테스트를 mock/moto/LocalStack/허용된 sandbox에 적용하고 어느 실패가 어느 층에서만 드러나는지 기록하세요. 실제 자원 생성은 별도 승인된 테스트 계정과 정리 정책을 따라야 합니다.

## 5. 적용 과제

‘mock에서는 업로드 성공, 운영에서는 AccessDenied’ 사건을 분석하세요. 어느 테스트가 빠졌고 어떤 최소 sandbox 검사로 보완할지, 단위 테스트에 운영 키를 넣지 않고 설명합니다.

보강: 이 본문의2026-10-02 검증 범위 이후,2026-10-06에는 moto 5.0.28 기반 S3 계약 테스트를 추가 실행했습니다. [10-7](07-python-toolkit.md)에 버전·성공/오류 시나리오와 남은 한계를 기록했습니다. 실제 AWS IAM이나 Stubber 검증을 추가한 것은 아닙니다.

## 퀴즈

### Q1

함수 mock 성공은 실제 IAM 권한 검증인가?

### Q2

LocalStack은 모든 AWS 운영 특성이 완전히 같은가?

### Q3

Stubber와 실제 sandbox의 검증 범위 차이는?

### Q4

S3 Body를 bytes로만 대체할 때 놓칠 수 있는 두 가지는?

### Q5

빠른 테스트와 실제 계약 확인을 조합한 S3 테스트 구성을 제안하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [botocore Stubber](https://botocore.amazonaws.com/v1/documentation/api/latest/reference/stubber.html), [moto](https://docs.getmoto.org/en/latest/) — 후속 읽기.
- [실제 LocalStack 검증](../04-fastapi/04-localstack.md).

확인일: 2026-10-02. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
