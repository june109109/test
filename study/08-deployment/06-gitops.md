# 8-6. 이미지 배포·Kubernetes·GitOps

[목차](../README.md) · [정답·해설](06-gitops-answers.md)

예상 55분. 목표: 이미지 다운로드와 배포 제어를 구분하고, 선언 상태를 실제 상태와 맞추는 루프를 설명합니다.

## 1. 세 가지 서로 다른 변화

컨테이너는 앱의 배포 산출물을 이미지로 묶습니다. Kubernetes는 원하는 수의 workload와 서비스 자원을 선언하고 controller가 실제 상태를 맞춥니다. GitOps는 버전 관리된 선언을 기준으로 agent/controller가 변경을 확인하고 적용·조정하는 운영 방식입니다.

이미지를 registry에서 **pull**한다는 사실과 배포 명령이 어느 쪽에서 시작되는지는 다릅니다. Jenkins가 `kubectl apply`로 변경을 push해도 노드는 이미지를 pull합니다. 컨테이너를 쓴다고 자동으로 GitOps가 되는 것은 아닙니다.

```text
CI: 소스 → 검증 → 이미지 빌드 → registry에 digest 게시
배포 선언: digest/설정 변경을 버전 관리
GitOps controller: 선언 확인 → 클러스터 실제 상태와 비교 → 조정
노드: 지정한 이미지 가져오기 → 컨테이너 실행
```

## 2. 선언과 reconciliation

`replicas: 3`은 프로세스 세 개를 한 번 실행하라는 명령과 다릅니다. controller가 실제 상태를 관찰하며 원하는 수로 맞추려 합니다. 하지만 자원 부족·이미지 오류·권한·잘못된 probe가 있으면 원하는 상태에 도달하지 못할 수 있습니다.

Kubernetes가 있다고 데이터 무결성·앱 버그·효율적 용량이 자동 해결되지는 않습니다. Deployment, Service, readiness, 종료 신호·grace period 등의 계약을 앱이 따라야 합니다.

## 3. 비용 비교

| 안 | 이익 | 비용 |
| --- | --- | --- |
| VM+스크립트 | 작은 규모에서 단순 | 대상별 상태·복구 직접 구현 |
| 관리형 컨테이너 서비스 | 배포 단위·자원 관리 단순화 | 제품 제약·비용 |
| Kubernetes | 선언적 제어·스케줄링·생태계 | 클러스터·네트워크·권한·업그레이드 복잡도 |
| GitOps 추가 | 선언 변경의 이력·재조정 | 동기화 정책·secret·긴급 변경 처리 |

팀이 운영할 수 없는 복잡도를 도입하면 자동화의 이익보다 장애 대응 비용이 커질 수 있습니다. 작은 서비스에서 k8s를 생략하는 것도 설계 결정입니다.

## 4. drift와 긴급 조치

수동으로 클러스터 설정을 바꾸면 Git 선언과 실제가 달라지는 drift가 생깁니다. 자동 동기화가 이를 되돌릴 수 있으므로 긴급 변경 때 동기화·선언 갱신·재개 절차가 필요합니다. 변경 승인과 배포 실행 권한도 별도 역할로 설계합니다.

Git에 secret 평문을 넣는 것이 GitOps의 필수 조건은 아닙니다. 외부 secret 저장소나 적절한 암호화·키 관리 경로를 이용합니다. declarative 상태가 있다고 런타임 데이터 백업이 불필요해지는 것도 아닙니다.

## 5. 적용 과제

‘Jenkins가 이미지를 빌드하고 kubectl로 배포’와 ‘Jenkins는 이미지/선언 변경까지만, controller가 동기화’의 자격증명 위치·장애·감사·복구 경로를 비교하세요.

## 퀴즈

### Q1

노드가 이미지를 pull하면 반드시 GitOps인가?

### Q2

replicas: 3을 선언하면 어떤 상황에서도 즉시 3개가 준비되는가?

### Q3

CI와 GitOps controller의 역할을 구분하라.

### Q4

수동 긴급 변경과 자동 동기화가 충돌할 수 있는 이유는?

### Q5

작은 팀의 컨테이너 배포에 Kubernetes/GitOps를 도입할 조건과 비용을 비교하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [Kubernetes Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/) — 선언·rollout·surge 동작을 확인했습니다.
- [Argo CD 문서](https://argo-cd.readthedocs.io/en/stable/) — 추가 읽기; 이번 접근은 403. 실제 클러스터·GitOps 서비스는 설치하지 않았습니다.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
