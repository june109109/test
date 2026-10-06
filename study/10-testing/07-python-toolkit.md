# 10-7. moto·AnyIO·polyfactory를 함께 쓰는 테스트

[목차](../README.md) · [정답·해설](07-python-toolkit-answers.md)

예상 70분. 목표: 기존 수동 factory·pytest-asyncio 예제에 대안을 추가하고, 모의 AWS 검증의 범위를 정확하게 설명합니다.

## 1. 파일과 실행

[계약 테스트](../labs/python_track_tests/test_toolkit.py), [exporter 테스트](../labs/python_track_tests/test_metrics.py), [pytest 설정](../labs/python_track_tests/pytest.ini), [의존성](../labs/requirements-python-track.txt).

```bash
python3 -m venv /tmp/study-track
/tmp/study-track/bin/python -m pip install -r study/labs/requirements-python-track.txt
/tmp/study-track/bin/python -m pytest -q   -c study/labs/python_track_tests/pytest.ini study/labs/python_track_tests   --junitxml=/tmp/python-track-new.xml
```

2026-10-06에 별도 가상환경 `/workspace/study-track`에서 **7 passed**였습니다. [JUnit 기록](../results/python-track-2026-10-06.xml)에 사례별 결과를 보존했습니다. botocore 1.35.99의 datetime.utcnow 사용에 대한 DeprecationWarning 11건이 있었으며 숨기지 않았습니다. 통과·경고·미실행을 구분합니다.

## 2. AnyIO와 pytest-asyncio 선택

기존 10-2는 pytest-asyncio의 strict 모드와 명시적 async fixture를 사용했습니다. 이번 예제는 AnyIO plugin의 marker와 backend fixture를 사용합니다.

```python
@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.mark.anyio
async def test_something():
    ...
```

이것은 설정 형태 발췌입니다. 실제 파일에는 S3 계약 검증과 assert가 있습니다. backend를 고정하지 않으면 설정에 따라 Trio 등 추가 backend도 대상이 될 수 있습니다. asyncio 전용 코드를 써놓고 모든 backend 호환을 주장하지 않습니다. 두 plugin의 자동 모드를 동시에 켜지 않으며, 이번 pytest.ini는 pytest-asyncio를 strict로 두어 담당을 분리합니다.

## 3. moto의 수명과 가짜 자격증명

fixture의 `with mock_aws():` 안에서 boto3 client와 고유 bucket을 만듭니다. 종료할 때 client를 닫고 moto context의 메모리 상태를 버립니다. 실제 AWS 버킷을 만들거나 운영 자격증명을 읽지 않도록 client에 학습용 `test` 키와 region을 명시했습니다.

동기 SDK는 AnyIO 스레드로 넘깁니다. mock context는 해당 스레드 작업이 끝날 때까지 살아 있어야 합니다. get_object의 Body는 try/finally로 읽고 닫습니다. 이 fixture의 수명/오프로딩은 실제 네트워크 대기를 모사한 성능 결과가 아닙니다.

| 검증 | 기대값 | 의미/한계 |
| --- | --- | --- |
| 빈/텍스트/바이너리 payload 왕복 3개 | 원본 bytes 일치 | 인코딩·빈 값 처리 계약 |
| 없는 객체 1개 | NoSuchKey·HTTP404 | 오류의 의미 보존 |
| factory 1개 | 다른 객체·명시 값 유지 | 공유 객체의 상태 누출 방지의 기초 |
| TTL 1개 | 9.999초 hit·10초 miss | sleep 없이 만료 경계 확인 |
| exporter 1개 | lag·토큰 2개·응답 6개·지표·422 | 9-7의 앱 계측; 대시보드 실행은 별도 |

## 4. polyfactory가 정답을 결정하지는 않는다

Document dataclass를 DataclassFactory에 연결하고 key/payload는 각 사례에서 명시적으로 override합니다. 이렇게 하면 타입 기반 기본 생성의 편리함과 업무 경계의 명시성을 함께 얻습니다. 무작위 값이 우연히 원하는 경계를 밟길 기대하지 않습니다.

작은 두 필드 모델은 수동 생성도 충분히 쉽습니다. polyfactory의 이익은 필드가 많거나 중첩 모델의 유효 기본값이 반복될 때 커지고, 도구 버전·생성 제약·모델 변경의 유지 비용이 추가됩니다. immutable dataclass여도 중첩 mutable 값의 공유는 별도로 점검해야 합니다.

## 5. 어디까지 믿을 수 있을까

moto 테스트는 실제 IAM·리전 차이·S3 망 지연·retry·서비스 제한을 검증하지 않습니다. 기존 4-4의 LocalStack 실제 HTTP 180회 검증과 계약을 맞추고, 필요한 실제 서비스 차이는 허용된 sandbox에서 작게 확인합니다. mock과 통합 검증의 이익/비용을 10-4·10-5와 함께 비교하세요.

AnyIO 전환이 모든 I/O를 비동기화한 것도 아닙니다. 이 테스트는 동기 boto3를 명시적으로 offload했습니다. aioboto3의 호환성과 실행은 별도 후보입니다.

## 6. 적용 과제

같은 read_bytes 계약을 LocalStack에 적용할 때 바뀌는 준비·endpoint·정리와 바뀌지 않아야 할 본문/오류 의미를 적으세요. 새 테스트에서 response 객체의 내부 구현보다 소비자가 의존하는 내용·오류·수명을 검증합니다.

## 퀴즈

### Q1

AnyIO marker를 붙이면 자동으로 모든 backend에서 정상 작동하는가?

### Q2

moto 테스트 통과는 실제 IAM 권한 확인인가?

### Q3

factory가 있어도 payload 경계값을 명시한 이유는?

### Q4

mock_aws context와 실행 중인 스레드의 수명 관계는?

### Q5

단위/moto/LocalStack/실제 sandbox 검증을 비용과 누락 범위를 고려해 설계하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- 설치·실행한 버전: moto 5.0.28, polyfactory 2.19.0, cachetools 5.5.1, prometheus-client 0.21.1, boto3/botocore 1.35.99, AnyIO 4.14.2, pytest 8.3.5.
- [moto](https://docs.getmoto.org/en/latest/docs/getting_started.html), [AnyIO testing](https://anyio.readthedocs.io/en/stable/testing.html)는 이번 웹 접근에서 HTTP 403으로 직접 확인하지 못했습니다. 동작 근거는 설치한 버전의 실행 테스트입니다.
- [polyfactory](https://polyfactory.litestar.dev/latest/)는 추가 참고 문서이며 사용한 API는 설치 버전으로 검증했습니다.

확인일: 2026-10-06. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
