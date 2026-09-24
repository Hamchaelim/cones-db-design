# CONES 칸반 보드 DB Schema

과제#3에서 실제 사용한 GitHub Projects 보드(cones project)를 역설계한 스키마.
대상 데이터: seune-h0203/cones 저장소의 Issue + Projects V2 보드(Todo / In Progress / Done)

---

## projects
보드(프로젝트) 자체. 지금은 1행(cones project)이지만, 보드를 여러 개 관리할 수 있게 분리한다.

| Column Name            | Type      | Constraint |
| ---------------------- | --------- | ---------- |
| project_id             | SERIAL    | PK         |
| project_name           | TEXT      | NOT NULL   |
| github_repo_full_name  | TEXT      | UK         |
| github_project_number  | INT       | Nullable   |
| created_at             | TIMESTAMP | NOT NULL   |

---

## users
담당자. 이름이 카드마다 반복되므로 분리한다.

| Column Name     | Type      | Constraint |
| --------------- | --------- | ---------- |
| user_id         | SERIAL    | PK         |
| github_username | TEXT      | UK         |
| display_name    | TEXT      | Nullable   |
| created_at      | TIMESTAMP | NOT NULL   |

---

## statuses
보드의 칸(Todo / In Progress / Done). 칸 추가·순서 변경을 데이터로 처리하기 위해 테이블로 둔다.

| Column Name | Type    | Constraint                       |
| ----------- | ------- | -------------------------------- |
| status_id   | SERIAL  | PK                               |
| project_id  | INT     | FK → projects(project_id)        |
| status_name | TEXT    | NOT NULL                         |
| position    | INT     | NOT NULL, CHECK (position >= 0)  |
| is_done     | BOOLEAN | NOT NULL, default false          |

- UNIQUE(project_id, status_name)
- UNIQUE(project_id, position)

---

## milestones
여러 카드가 공유하는 목표. 없는 카드가 있으므로 tasks에서는 Nullable.

| Column Name              | Type | Constraint                                  |
| ------------------------ | ---- | ------------------------------------------- |
| milestone_id             | SERIAL | PK                                        |
| project_id               | INT  | FK → projects(project_id)                   |
| github_milestone_number  | INT  | Nullable                                    |
| title                    | TEXT | NOT NULL                                    |
| state                    | TEXT | NOT NULL, CHECK (state IN ('open','closed'))|
| due_date                 | DATE | Nullable                                    |

- UNIQUE(project_id, github_milestone_number)

---

## tasks
카드(Issue). 보드 위치(status_id)와 이슈 열림/닫힘(issue_state)은 서로 다른 값이므로 반드시 분리해 저장한다.

| Column Name         | Type      | Constraint                                        |
| ------------------- | --------- | ------------------------------------------------- |
| task_id             | SERIAL    | PK                                                |
| project_id          | INT       | FK → projects(project_id)                         |
| status_id           | INT       | FK → statuses(status_id)                          |
| milestone_id        | INT       | FK → milestones(milestone_id), Nullable           |
| author_id           | INT       | FK → users(user_id), Nullable                     |
| github_issue_number | INT       | NOT NULL                                          |
| title               | TEXT      | NOT NULL                                          |
| body                | TEXT      | Nullable                                          |
| issue_state         | TEXT      | NOT NULL, CHECK (issue_state IN ('open','closed'))|
| created_at          | TIMESTAMP | NOT NULL                                          |
| closed_at           | TIMESTAMP | Nullable                                          |

- UNIQUE(project_id, github_issue_number)
- CHECK (closed_at IS NULL OR closed_at >= created_at)

---

## task_assignees
카드와 담당자의 N:M 관계. 카드 1개에 담당자 여러 명, 담당자 1명이 카드 여러 개를 맡을 수 있어 중간 테이블이 필요하다.

| Column Name | Type      | Constraint                     |
| ----------- | --------- | ------------------------------ |
| task_id     | INT       | PK, FK → tasks(task_id)        |
| user_id     | INT       | PK, FK → users(user_id)        |
| assigned_at | TIMESTAMP | NOT NULL                       |

- 복합 PK (task_id, user_id) → 같은 사람이 같은 카드에 중복 배정되는 것을 DB가 막는다.

---

## (선택) labels / task_labels
CONES 보드는 GitHub Label 대신 제목 접두사([QA], [BE], [FE], [DEPLOY], [PRESENTATION])로 작업 종류를 구분했다.
이 분류로 통계를 내려면 아래 두 테이블을 추가한다. 필요 없으면 생략한다.

### labels
| Column Name | Type   | Constraint                |
| ----------- | ------ | ------------------------- |
| label_id    | SERIAL | PK                        |
| project_id  | INT    | FK → projects(project_id) |
| label_name  | TEXT   | NOT NULL                  |

- UNIQUE(project_id, label_name)

### task_labels
| Column Name | Type | Constraint               |
| ----------- | ---- | ------------------------ |
| task_id     | INT  | PK, FK → tasks(task_id)  |
| label_id    | INT  | PK, FK → labels(label_id)|

---

## 삭제 정책
- projects 삭제 시 statuses, milestones, tasks는 ON DELETE CASCADE
- tasks 삭제 시 task_assignees, task_labels는 ON DELETE CASCADE
- users 삭제 시 tasks.author_id는 ON DELETE SET NULL

## 데이터 입력 순서 (FK 때문에 반드시 이 순서)
projects → users → statuses → milestones → tasks → task_assignees → (labels → task_labels)
