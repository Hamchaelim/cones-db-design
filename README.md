# CONES Board Database Design

이 저장소는 `seune-h0203/cones` 프로젝트의 GitHub Projects 보드 데이터를 역설계한 데이터베이스 스키마를 정리한 저장소입니다.

## 목적

GitHub Projects 보드의 카드, 상태, 담당자, 이슈 정보를 정규화하여 저장하고,
실제 프로젝트 관리 데이터가 효율적으로 조회되고 유지보수되도록 설계했습니다.

## 주요 테이블

- `projects`: 프로젝트 보드
- `users`: 담당자
- `statuses`: Todo / In Progress / Done 같은 보드 상태
- `milestones`: 카드 집합의 목표
- `tasks`: 이슈/카드
- `task_assignees`: 카드와 담당자의 N:M 관계

## 설계 포인트

- `status_id`와 `issue_state`를 분리하여 보드 위치와 이슈 열림/닫힘 상태를 구분
- `task_assignees`를 별도 테이블로 두어 여러 담당자 배정을 표현
- `ON DELETE CASCADE`, `ON DELETE SET NULL` 정책으로 무결성 유지
- `CHECK` 제약 조건으로 상태 값과 시간 조건 검증
- `labels` / `task_labels`는 현재 범위에서 제외

## 포함 파일

- `db.spec.md`: DB 스키마 명세서

## 데이터 확인 예시

```sql
SELECT * FROM public.projects;
SELECT * FROM public.users;
SELECT * FROM public.statuses;
SELECT * FROM public.tasks;
SELECT * FROM public.task_assignees;
```

## 참고

실제 CSV 데이터에서 다대다 담당자 관계가 확인되었고,
이는 `task_assignees` 테이블이 실제로 필요한 근거가 된다는 점을 반영하였습니다.
