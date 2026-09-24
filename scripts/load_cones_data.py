import json
from pathlib import Path

base = Path(__file__).resolve().parent.parent
raw = json.loads((base / 'data' / 'github-raw.json').read_text(encoding='utf-8'))
issues = raw['issues']


def sql_literal(value):
    if value is None:
        return 'NULL'
    return "'" + str(value).replace("'", "''") + "'"


def dollar_quote(value):
    if value is None:
        return 'NULL'
    text = str(value).replace('$', '$$')
    return '$$' + text + '$$'


# 1) Project
project_sql = [
    "INSERT INTO public.projects (project_id, project_name, github_repo_full_name, github_project_number, created_at)",
    "VALUES (1, 'cones', 'seune-h0203/cones', 1, NOW())",
    "ON CONFLICT (project_id) DO UPDATE SET project_name = EXCLUDED.project_name, github_repo_full_name = EXCLUDED.github_repo_full_name, github_project_number = EXCLUDED.github_project_number;",
]

# 2) Users
user_names = sorted({
    issue.get('user')
    for issue in issues
    if issue.get('user')
} | {
    assignee
    for issue in issues
    for assignee in issue.get('assignees', [])
    if assignee
})
user_rows = ', '.join(
    f"({sql_literal(name)}, {sql_literal(name)}, NOW())" for name in user_names
)
user_sql = [
    "INSERT INTO public.users (github_username, display_name, created_at) VALUES " + user_rows +
    " ON CONFLICT (github_username) DO UPDATE SET display_name = EXCLUDED.display_name;"
]

# 3) Statuses
status_rows = [
    "(1, 1, 'Todo', 0, FALSE)",
    "(2, 1, 'In Progress', 1, FALSE)",
    "(3, 1, 'Done', 2, TRUE)",
]
status_sql = [
    "INSERT INTO public.statuses (status_id, project_id, status_name, position, is_done) VALUES " + ', '.join(status_rows) +
    " ON CONFLICT (status_id) DO UPDATE SET status_name = EXCLUDED.status_name, position = EXCLUDED.position, is_done = EXCLUDED.is_done;"
]

# 4) Milestones (deduplicated)
milestones = []
seen = set()
for issue in issues:
    title = issue.get('milestone')
    number = issue.get('milestone_number')
    if not title:
        continue
    key = (number, title)
    if key in seen:
        continue
    seen.add(key)
    milestones.append((number, title))

milestone_rows = [
    f"(1, {number if number is not None else 'NULL'}, {dollar_quote(title)}, 'open', NULL)" for number, title in milestones
]
milestone_sql = []
if milestone_rows:
    milestone_sql.append(
        "INSERT INTO public.milestones (project_id, github_milestone_number, title, state, due_date) VALUES " + ', '.join(milestone_rows) +
        " ON CONFLICT (project_id, github_milestone_number) DO UPDATE SET title = EXCLUDED.title, state = EXCLUDED.state, due_date = EXCLUDED.due_date;"
    )

# 5) Tasks
all_tasks = []
for issue in issues:
    issue_number = issue['number']
    state = issue['state']
    status_id = 3 if state == 'closed' else 1
    milestone_number = issue.get('milestone_number')
    milestone_id_sql = f"(SELECT milestone_id FROM public.milestones WHERE project_id = 1 AND github_milestone_number = {milestone_number})" if milestone_number is not None else 'NULL'
    author_login = issue.get('user')
    author_id_sql = f"(SELECT user_id FROM public.users WHERE github_username = {sql_literal(author_login)})" if author_login else 'NULL'
    created_at = issue.get('created_at')
    closed_at = issue.get('closed_at')
    task_line = (
        f"(1, {status_id}, {milestone_id_sql}, {author_id_sql}, {issue_number}, {dollar_quote(issue.get('title'))}, "
        f"{dollar_quote(issue.get('body'))}, {sql_literal(state)}, {sql_literal(created_at)}, {sql_literal(closed_at)})"
    )
    all_tasks.append(task_line)

task_sql = [
    "INSERT INTO public.tasks (project_id, status_id, milestone_id, author_id, github_issue_number, title, body, issue_state, created_at, closed_at) VALUES "
    + ', '.join(all_tasks)
    + " ON CONFLICT (project_id, github_issue_number) DO UPDATE SET status_id = EXCLUDED.status_id, milestone_id = EXCLUDED.milestone_id, author_id = EXCLUDED.author_id, title = EXCLUDED.title, body = EXCLUDED.body, issue_state = EXCLUDED.issue_state, created_at = EXCLUDED.created_at, closed_at = EXCLUDED.closed_at;"
]

# 6) Assignees
assignee_rows = []
for issue in issues:
    task_sql_sub = f"(SELECT task_id FROM public.tasks WHERE project_id = 1 AND github_issue_number = {issue['number']})"
    for assignee in issue.get('assignees', []):
        if not assignee:
            continue
        user_sql_sub = f"(SELECT user_id FROM public.users WHERE github_username = {sql_literal(assignee)})"
        assignee_rows.append(f"({task_sql_sub}, {user_sql_sub}, NOW())")
assignee_sql = []
if assignee_rows:
    assignee_sql.append(
        "INSERT INTO public.task_assignees (task_id, user_id, assigned_at) VALUES " + ', '.join(assignee_rows) +
        " ON CONFLICT (task_id, user_id) DO NOTHING;"
    )

out_lines = ['BEGIN;'] + project_sql + user_sql + status_sql + milestone_sql + task_sql + assignee_sql + ['COMMIT;']
out_path = base / 'data' / 'cones_supabase_import.sql'
out_path.write_text('\n'.join(out_lines), encoding='utf-8')
print(f'wrote {out_path}')
print(f'users={len(user_names)} tasks={len(all_tasks)} assignees={len(assignee_rows)} milestones={len(milestones)}')
