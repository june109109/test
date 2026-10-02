# 4-4. LocalStack S3 호출을 동시 요청 10개로 비교하기

[목차](../README.md) · [이전](03-blocking-sdk.md) · [정답·해설](04-localstack-answers.md)

예상 80분. 목표: 실제 S3 호환 서비스를 동기 SDK로 호출하고, 실행 위치·대기·원본 응답의 정확성을 함께 확인합니다.

## 1. 무엇을 비교하나

같은 작은 S3 객체를 읽는 FastAPI 경로를 세 방식으로 만듭니다.

| 경로 | SDK 호출 위치 | 가설 |
| --- | --- | --- |
| async-direct | async 경로의 루프 스레드에서 직접 호출 | 호출·본문 읽기 동안 루프를 붙잡을 수 있음 |
| sync | def 경로, FastAPI의 스레드 실행 | 여러 호출의 대기 겹침 가능 |
| async-offload | async 경로에서 AnyIO 오프로딩 | 나머지 비동기 흐름과 동기 SDK 경계 분리 |

세 경로는 같은 client·bucket·key·응답 데이터·SDK 설정을 사용합니다. 객체를 한 번 읽고 캐시된 값을 되돌려 비교하는 것은 아닙니다. **각 측정 요청에서 실제 boto3 get_object와 Body.read가 실행됩니다.**

FastAPI 호출은 HTTPX의 ASGITransport로 같은 프로세스에서 실행합니다. boto3→LocalStack 구간은 실제 HTTP입니다. 따라서 Uvicorn·외부 LB·브라우저·실제 AWS의 성능을 측정한 실험은 아닙니다.

## 2. 버전과 준비

이 실습은 학습 재현을 위해 **LocalStack Community 4.0.0** 이미지를 고정했습니다. 현재 최신 제품·라이선스·기능 전체를 안내하는 문서가 아닙니다. 새 버전을 선택한다면 실행·인증·호환 요건을 별도로 확인하세요. 확인한 이미지 digest는 다음입니다.

```text
localstack/localstack@sha256:fae7a9a2c3eb86fc102df0fdb78b0a8624617734052bc163cb14ebb64d70a047
```

실행 환경: CPython 3.12.14, boto3/botocore 1.35.99, urllib3 2.8.0. FastAPI 등은 [의존성 파일](../labs/requirements-s3.txt)과 [결과 JSON](../results/localstack-s3-2026-10-01.json)을 참고합니다. 이 환경에는 `/workspace/study-python` 가상환경에 boto3를 추가했고 기존 FastAPI 패키지는 system-site-packages로 사용했습니다.

다른 환경에서는 독립 venv를 만들고 해당 의존성 파일을 설치할 수 있습니다. 이 목록은 모든 전이 의존성을 잠근 lockfile은 아닙니다. TLS·다운로드 검증을 끄지 말고 해당 환경의 신뢰 설정을 사용하세요.

## 3. 로컬 서비스 실행

아래는 이 관리형 환경에서 사용한 설정의 재실행 예입니다. Docker endpoint 선택자를 명시적으로 초기화해 로컬 데몬을 대상으로 합니다. 기존 Docker registry 인증·프록시 설정은 유지합니다. 이름이 이미 있으면 다른 실습 이름을 사용하고 기존 컨테이너를 임의로 지우지 마세요.

```bash
docker_local() {
  env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS \
    -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
    docker --host=unix:///var/run/docker.sock "$@"
}
docker_local run -d --name study-localstack-s3 \
  --label purpose=study-materials --memory=1g --cpus=1 \
  -p 127.0.0.1::4566 -e SERVICES=s3 -e EAGER_SERVICE_LOADING=1 \
  -e DISABLE_EVENTS=1 \
  --mount type=bind,src=/etc/ssl/certs/ca-certificates.crt,dst=/run/study-ca-bundle.pem,readonly \
  -e REQUESTS_CA_BUNDLE=/run/study-ca-bundle.pem \
  -e SSL_CERT_FILE=/run/study-ca-bundle.pem \
  localstack/localstack@sha256:fae7a9a2c3eb86fc102df0fdb78b0a8624617734052bc163cb14ebb64d70a047
docker_local port study-localstack-s3 4566/tcp
```

CA 경로와 로컬 Docker 소켓은 환경에 따라 다릅니다. 일반 개인 PC에서는 Docker의 정상 context와 신뢰 저장소를 사용하세요. 여기의 설정을 다른 환경에 무조건 복사할 필요는 없습니다. 컨테이너에 실제 AWS 키·Docker 소켓·사용자의 홈 디렉터리를 넘기지 않습니다.

출력된 임시 포트를 사용해 `http://127.0.0.1:포트/_localstack/health`의 S3 상태를 확인합니다. 이후 스크립트의 실제 bucket 생성·객체 쓰기·읽기가 기능 준비를 검증합니다. 건강 상태 응답만으로 S3 API 성공을 주장하지 않습니다.

## 4. 실행·자원 정리

[실습 코드](../labs/localstack_s3_compare.py)는 localhost/127.0.0.1의 명시적인 HTTP endpoint만 받습니다. `test`/`test`는 에뮬레이터용 가짜 자격증명이며 실제 AWS 키가 아닙니다. 기본 AWS credential chain에 기대지 않습니다. 생성한 UUID 기반 버킷과 객체만 삭제합니다.

```bash
cd /workspace/test
# 실제 docker port 출력에 맞춰 32768을 바꾸세요.
/workspace/study-python/bin/python study/labs/localstack_s3_compare.py \
  --endpoint http://127.0.0.1:32768 \
  --output /tmp/localstack-s3-my-run.json
```

다른 venv에서는 해당 Python 경로를 사용합니다. 끝난 뒤 자신이 위에서 만든 실습 컨테이너만 정리합니다.

```bash
docker_local rm -f study-localstack-s3
```

실제 실행에는 별도 이름 `study-localstack-20261001`을 사용했습니다. 결과 파일은 실습 데이터가 삭제됐는지도 기록합니다. 어떤 과정에서 실패했다면 출력 오류와 해당 실습 자원만 확인하고 다른 버킷을 정리하지 않습니다.

## 5. 두 조건의 실제 결과

2026-10-01 실행. 경로마다 동시 요청 10개, 각 조건 3회 중앙값. AnyIO token 40, SDK 보관 풀 설정 20, 총 시도 1로 재시도하지 않았습니다. LocalStack 컨테이너에는 CPU 1, 메모리 1GiB 제한을 두었습니다.

| 조건 | async-direct | sync | async-offload |
| --- | ---: | ---: | ---: |
| 실제 로컬 S3 읽기만 | 0.038017초 | 0.031502초 | 0.032058초 |
| SDK 직전에 50ms 동기 대기 추가 | 0.542589초 | 0.095670초 | 0.084910초 |

추가 50ms는 **코드에서 주입한 time.sleep이며 LocalStack 또는 AWS가 실제로 50ms 지연됐다는 뜻이 아닙니다.** 호출 위치가 미치는 영향을 분명히 보이기 위한 별도 조건입니다. 실제 네트워크 지연을 조작한 실험도 아닙니다.

총 `2조건×3경로×3회×10요청 = 180`개의 측정 읽기에서 객체 바이트·응답·업무 실행 스레드를 확인했습니다. 준비·워밍업 읽기는 이 수에 포함하지 않습니다. 종료 시 자신이 만든 객체·버킷을 삭제하고 HeadBucket이 404인지 확인했습니다.

## 6. 숫자가 말하는 것과 말하지 않는 것

기본 조건의 차이는 작습니다. 로컬 객체가 작고 응답이 빨라 스레드·ASGI·에뮬레이터 오버헤드가 상대적으로 큽니다. ‘차이가 작으니 직접 호출해도 항상 안전’이라고 결론 내릴 수 없습니다. 루프를 점유한다는 실행 경계는 확인됐고, 느린 호출이 생기면 영향이 커질 수 있습니다.

주입 조건에서는 직접 호출이 약 10×50ms 대기를 직렬로 포함하며 나머지는 대기를 겹쳤습니다. sync와 offload의 작은 차이로 어느 방식이 보편적으로 빠르다고 판단하지 않습니다. 실제 앱에서는 연결·본문 크기·재시도·CPU·하류 제한이 달라집니다.

LocalStack은 AWS 서비스의 일부 동작을 로컬에서 검증하는 도구입니다. 실제 IAM·네트워크·TLS·운영 제한·모든 API 예외를 동등하게 검증한 것으로 해석하지 않습니다. 이 구분을 10장의 통합 테스트에서 다시 다룹니다.

## 적용 과제

먼저 기본 조건만 보고 결론을 써 본 뒤 주입 조건을 추가해 수정하세요. ‘실제로 관찰한 사실’과 ‘운영에 대한 가설’을 두 열로 나눕니다. 객체 크기·동시 요청·SDK timeout 중 다음에 바꿀 변수 하나와 기대·반대 결과를 적습니다.

## 퀴즈

Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 권장 통과 8점.

### Q1
추가 50ms 조건을 ‘LocalStack의 실제 네트워크 지연이 50ms’라고 보고해도 되나요?

### Q2
에뮬레이터의 health 응답만 성공하면 실제 get_object도 검증된 것인가요?

### Q3
기본 조건에서 시간 차이가 작았다고 async 직접 호출이 루프를 안 막는다는 증거가 되나요? 구분할 두 측면을 설명하세요.

### Q4
이 실험에서 검증한 것 두 가지, 실제 AWS에 대해 검증하지 않은 것 두 가지를 적으세요.

### Q5
실제 S3 API의 응답이 때때로 3초 걸립니다. 위 결과를 참고해 코드·동시성·timeout·관측·실제 환경 검증을 설계하세요.

## 출처·실행 근거

- [실험 코드](../labs/localstack_s3_compare.py), [원본 JSON](../results/localstack-s3-2026-10-01.json).
- [LocalStack 공개 저장소](https://github.com/localstack/localstack): 제품·구현 참고. 이 편의 실행 증거는 고정 이미지의 기능 요청 결과입니다.
- [boto3 client 가이드](https://github.com/boto/boto3/blob/develop/docs/source/guide/clients.rst): client의 동시 사용·프로세스 제한.

문서 사이트의 일부 페이지는 이 환경에서 403을 반환해 읽지 못했습니다. 현재 최신 LocalStack의 계정·토큰 요건을 확인했다고 주장하지 않습니다. 위 고정 이미지의 Community 4.0.0 실행과 S3 기능은 직접 확인했습니다.
