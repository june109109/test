# 8-2. Docker 이미지 만들기

[목차](../README.md) · [정답·해설](02-docker-answers.md)

예상 55분. 목표: 이미지와 실행 상태를 구분하고, 멀티스테이지 빌드의 이익과 재현성 한계를 설명합니다.

## 1. 이미지와 컨테이너

이미지는 파일시스템 레이어와 실행 메타데이터로 구성한 배포 단위입니다. 컨테이너는 그 이미지로 시작한 실행 인스턴스이며 쓰기 계층·프로세스·네트워크·자원 제한이 있습니다. 이미지에 포함되지 않은 DB 데이터·업로드·설정·secret은 별도 수명을 가집니다.

태그는 바뀔 수 있는 이름입니다. 같은 `latest`라도 시점에 따라 다른 바이트를 가리킬 수 있습니다. 배포는 빌드 산출물 digest를 기록해 어떤 이미지가 실행되었는지 추적합니다. digest 고정은 업데이트를 없애는 것이 아니라 업데이트를 명시적으로 검토하는 방법입니다.

## 2. 멀티스테이지의 역할

빌드 단계에는 compiler·헤더·패키지 설치 도구를 두고, 런타임 단계에는 실행에 필요한 산출물만 복사할 수 있습니다. 이미지 크기와 불필요한 도구를 줄이지만 취약점이 자동으로 사라지는 것은 아닙니다.

다음은 **개념용 템플릿**이며 그대로 빌드 검증하지 않았습니다. `requirements.lock`과 `app/`은 이 자료 저장소의 실제 파일이 아니라 대상 앱에서 준비할 파일입니다.

```dockerfile
FROM python:3.12-slim AS build
WORKDIR /build
COPY requirements.lock .
RUN python -m pip wheel --wheel-dir /wheels -r requirements.lock

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=build /wheels /wheels
COPY requirements.lock .
RUN python -m pip install --no-index --find-links=/wheels -r requirements.lock     && rm -rf /wheels
COPY app/ ./app/
USER 10001:10001
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

실사용에서는 base digest와 완전한 의존성 고정·hash 검증, 네이티브 패키지의 런타임 라이브러리, CPU 아키텍처, 쓰기 가능한 디렉터리를 추가 확인합니다. build와 runtime의 ABI가 달라 wheel이 동작하지 않을 수 있습니다. 삭제한 /wheels가 이전 COPY 레이어의 바이트까지 없애는 것도 아니므로 더 작은 이미지는 BuildKit mount 등으로 개선할 수 있습니다.

## 3. 레이어 캐시와 build context

의존성 파일을 먼저 복사하고 설치한 뒤 자주 바뀌는 앱 코드를 복사하면 코드 변경 때 패키지 단계 캐시를 재사용하기 쉽습니다. `.dockerignore`로 .git·가상환경·캐시·로컬 secret 등을 build context에서 제외합니다.

`ARG SECRET=...`나 COPY 후 삭제로 secret을 숨기려 하지 않습니다. 레이어·메타데이터에 흔적이 남을 수 있습니다. 빌드 자격증명은 지원되는 secret mount, 런타임 자격증명은 런타임 secret 제공 경로를 씁니다.

## 4. 프록시와 CA가 있는 빌드 환경

이 클라우드에서는 Docker의 프록시 설정을 유지하고 HTTPS 접근이 필요한 build 단계에 제공된 CA를 read-only mount해야 할 수 있습니다. `--insecure`나 TLS 검증 비활성화로 설치를 통과시키지 않습니다. CA 경로·프록시 주소·자격증명을 일반 이미지에 복사하지 않습니다.

앞선 LocalStack/PostgreSQL은 공식 이미지를 pull하고 실행한 검증입니다. 이 Dockerfile로 앱 이미지를 build·실행한 증거는 아닙니다.

## 5. 적용 과제

자신의 앱에서 빌드에만 필요한 패키지, 실행 중 쓸 디렉터리, 이미지에 넣지 않을 설정을 구분하세요. 동일 digest 이미지의 시작·health check·정상 요청·종료를 검증할 절차도 적습니다.

## 퀴즈

### Q1

이미지 태그가 같으면 항상 같은 바이트인가?

### Q2

멀티스테이지면 취약점이 자동 제거되는가?

### Q3

의존성 파일을 앱 코드보다 먼저 COPY하는 이점은?

### Q4

secret을 COPY하고 다음 RUN에서 삭제하는 방법의 문제는?

### Q5

Python 앱 이미지를 재현 가능하게 빌드·검증할 계획을 작성하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/) — FROM 단계 분리와 COPY --from을 확인했습니다.
- 예제 템플릿은 독자 적용 과제이며 실행 결과가 아닙니다.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
