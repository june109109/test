# 8-5. Ansible과 반복 가능한 변경

[목차](../README.md) · [정답·해설](05-ansible-answers.md)

예상 45분. 목표: 명령 재실행과 상태 수렴의 차이를 설명하고, 여러 호스트의 변경 범위를 제한합니다.

## 1. 명령을 다시 보내는 것과 원하는 상태

`echo 설정 >> 파일`은 실행할 때마다 줄이 늘 수 있습니다. 반면 파일 내용이 원하는 템플릿과 같도록 맞추는 작업은 두 번째 실행에서 바뀔 것이 없도록 만들 수 있습니다. 같은 입력을 다시 적용해도 의도한 상태가 유지되는 성질을 이 문맥에서 멱등성이라고 합니다.

Ansible은 inventory의 대상에 playbook을 실행하여 패키지·파일·서비스 등의 상태를 관리합니다. 많은 모듈이 상태 기반 작업을 제공하지만 모든 playbook이 자동으로 멱등적인 것은 아닙니다. shell/command 작업과 외부 부작용은 직접 설계해야 합니다.

## 2. 개념용 playbook

아래는 구조 설명용입니다. 실제 inventory·파일·권한이 없고 실행하지 않았습니다.

```yaml
- hosts: app
  serial: 1
  tasks:
    - name: Install reviewed application configuration
      ansible.builtin.template:
        src: app.conf.j2
        dest: /etc/example-app/app.conf
        mode: '0640'
      notify: Restart application
  handlers:
    - name: Restart application
      ansible.builtin.service:
        name: example-app
        state: restarted
```

handler는 변경이 발생할 때 관련 동작을 모을 수 있습니다. 실제 앱의 설정 문법 검증·파일 소유자·서비스 사용자·health 확인·traffic drain은 별도로 넣어야 합니다. `serial: 1`만으로 무중단이 보장되지는 않습니다.

## 3. 비교

| 방식 | 이익 | 비용 |
| --- | --- | --- |
| 수동 SSH | 즉각적인 조사·조치 | 재현·감사·누락·대상 착오 |
| 반복 shell 스크립트 | 빠른 자동화 | 조건·에러·멱등성·복구 직접 구현 |
| Ansible 상태 모듈 | 반복 적용·호스트별 일관성 | inventory·변수·버전·권한 관리 |
| 불변 이미지 교체 | 런타임 변경 감소 | 이미지 빌드·교체·데이터 외부화 |

Ansible과 이미지 배포는 함께 사용할 수도 있습니다. host 패키지·계정·서비스를 Ansible로 관리하고 앱은 컨테이너로 실행하는 식입니다.

## 4. check mode와 실패 범위

check/diff mode는 예상 변경을 검토하는 데 도움을 주지만 모든 모듈·명령의 실제 실행을 정확히 예측하지 못합니다. diff에 secret이 노출될 수 있는 설정도 주의합니다. 검증 모드 성공을 실제 health 검증으로 간주하지 않습니다.

작은 대상군에서 먼저 적용하고 결과를 본 뒤 확대합니다. 일부 호스트 실패 시 중단·재실행·롤백 범위를 정합니다. 여러 호스트의 변경은 하나의 원자적 transaction이 아닙니다.

## 5. 적용 과제

첫 실행은 설정을 바꾸고 서비스가 한 번 재시작하며, 두 번째 실행은 변경·재시작이 없는 목표를 적으세요. 호스트 하나의 디스크가 꽉 찼을 때 나머지 호스트를 어떻게 처리할지도 정합니다.

## 퀴즈

### Q1

Ansible로 실행하면 모든 shell 작업이 자동 멱등적인가?

### Q2

check mode 성공은 실제 배포 성공과 같은가?

### Q3

append 명령과 template 기반 상태 관리의 차이는?

### Q4

serial: 1이 줄여 주는 위험과 보장하지 않는 것은?

### Q5

반복 적용·부분 실패·검증을 포함한 설정 배포 절차를 설계하라.

배점: Q1·Q2 각 1점, Q3·Q4 각 2점, Q5 4점. 8점 이상을 목표로 합니다.

## 출처와 범위

- [Ansible playbooks introduction](https://docs.ansible.com/ansible/latest/playbook_guide/playbooks_intro.html) — 추가 읽기. 이번 환경의 문서 접근은 403으로 실패했으며 playbook도 실행하지 않았습니다.

확인일: 2026-10-01. 사례의 숫자는 별도 실행 결과 링크가 없으면 설명용 가정입니다.
