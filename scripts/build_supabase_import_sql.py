import json
from pathlib import Path

base = Path(__file__).resolve().parent.parent
raw = json.loads((base / 'data' / 'github-raw.json').read_text(encoding='utf-8'))
issues = raw['issues']

project_id = 1
project_name = 'cones'
repo_full_name = 'seune-h0203/cones'

users = set()
for issue in issues:
    if issue.get('user'):
        users.add(issue['user'])
    for assignee in issue.get('assignees', []):
        if assignee:
            users.add(assignee)

user_rows = []
for user in sorted(users):
    user_rows.append(f"({user!r}, {user!r})")

status_rows = [
    (1, 1, 'Todo', 0, False),
    (2, 1, 'In Progress', 1, False),
    (3, 1, 'Done', 2, True),
]

milestone_map = {}
for issue in issues:
    milestone = issue.get('milestone')
    if not milestone:
        continue
    milestone_map.setdefault(issue.get('milestone_number') or f"{milestone}-{len(milestone_map)}", milestone)

milestones = []
for issue in issues:
    milestone = issue.get('milestone')
    if not milestone:
        continue
    number = issue.get('milestone_number')
    state = 'open'
    milestones.append((project_id, number, milestone, state, None))

seen = set()
for item in milestones:
    if item[1] is None:
        continue
    if item[1] not in seen:
        seen.add(item[1])

# dedupe by milestone number or title
final_milestones = {}
for project_id_local, number, title, state, due_date in milestones:
    key = number if number is not None else title
    final_milestones.setdefault(key, (project_id_local, number, title, state, due_date))

# build SQL
lines = []
lines.append("BEGIN;")
lines.append("INSERT INTO public.projects (project_id, project_name, github_repo_full_name, github_project_number, created_at) VALUES")
lines.append(f"  ({project_id}, '{project_name}', '{repo_full_name}', 1, NOW())")
lines.append("ON CONFLICT (project_id) DO UPDATE SET")
lines.append("  project_name = EXCLUDED.project_name,")
lines.append("  github_repo_full_name = EXCLUDED.github_repo_full_name,")
lines.append("  github_project_number = EXCLUDED.github_project_number;")

lines.append("INSERT INTO public.users (github_username, display_name, created_at) VALUES")
users_sql = ',\n'.join(f"  ('{user}', '{user}', NOW())" for user in sorted(users))
lines.append(users_sql + " ON CONFLICT (github_username) DO UPDATE SET display_name = EXCLUDED.display_name;")

lines.append("INSERT INTO public.statuses (status_id, project_id, status_name, position, is_done) VALUES")
status_sql = ',\n'.join(f"  ({sid}, {pid}, '{name}', {pos}, {str(done).lower()})" for sid, pid, name, pos, done in status_rows)
lines.append(status_sql + " ON CONFLICT (status_id) DO UPDATE SET status_name = EXCLUDED.status_name, position = EXCLUDED.position, is_done = EXCLUDED.is_done;")

if final_milestones:
    lines.append("INSERT INTO public.milestones (project_id, github_milestone_number, title, state, due_date) VALUES")
    milestone_sql = []
    for _, number, title, state, due_date in final_milestones.values():
        milestone_sql.append(f"  ({project_id}, {number if number is not None else 'NULL'}, '{title.replace("'", "''")}', '{state}', NULL)")
    lines.append(',\n'.join(milestone_sql) + " ON CONFLICT (project_id, github_milestone_number) DO UPDATE SET title = EXCLUDED.title, state = EXCLUDED.state, due_date = EXCLUDED.due_date;")

lines.append("INSERT INTO public.tasks (project_id, status_id, milestone_id, author_id, github_issue_number, title, body, issue_state, created_at, closed_at) VALUES")
insert_tasks = []
for issue in issues:
    login = issue.get('user')
    status_id = 3 if issue.get('state') == 'closed' else 1
    milestone_title = issue.get('milestone')
    milestone_id = 'NULL'
    if milestone_title:
        matches = [val for val in final_milestones.values() if val[2] == milestone_title]
        if matches:
            milestone_id = str(matches[0][0])
    author_id = 'NULL'
    if login:
        author_id = f"(SELECT user_id FROM public.users WHERE github_username = '{login}')"
    title = issue.get('title', '').replace("'", "''")
    body = issue.get('body')
    if body is None:
        body_sql = 'NULL'
    else:
        body_sql = "'" + str(body).replace("'", "''") + "'"
    created = issue.get('created_at', 'NOW()')
    closed = issue.get('closed_at')
    closed_sql = 'NULL' if not closed else "TIMESTAMPTZ '" + closed + "'"
    created_sql = "TIMESTAMPTZ '" + created + "'"
    insert_tasks.append(
        f"  ({project_id}, {status_id}, {milestone_id}, {author_id}, {issue.get('number')}, '{title}', {body_sql}, '{issue.get('state')}', {created_sql}, {closed_sql})"
    )

lines.append(',\n'.join(insert_tasks) + " ON CONFLICT (project_id, github_issue_number) DO UPDATE SET status_id = EXCLUDED.status_id, milestone_id = EXCLUDED.milestone_id, author_id = EXCLUDED.author_id, title = EXCLUDED.title, body = EXCLUDED.body, issue_state = EXCLUDED.issue_state, created_at = EXCLUDED.created_at, closed_at = EXCLUDED.closed_at;")

lines.append("INSERT INTO public.task_assignees (task_id, user_id, assigned_at) VALUES")
assignee_inserts = []
for issue in issues:
    issue_number = issue.get('number')
    task_selector = f"(SELECT task_id FROM public.tasks WHERE project_id = {project_id} AND github_issue_number = {issue_number})"
    for login in issue.get('assignees', []):
        if not login:
            continue
        user_selector = f"(SELECT user_id FROM public.users WHERE github_username = '{login}')"
        assignee_inserts.append(f"  ({task_selector}, {user_selector}, NOW())")

if assignee_inserts:
    lines.append(',\n'.join(assignee_inserts) + " ON CONFLICT (task_id, user_id) DO NOTHING;")
else:
    lines.append("VALUES (NULL, NULL, NOW()) ON CONFLICT DO NOTHING;")

lines.append("COMMIT;")

out = base / 'data' / 'cones_supabase_import.sql'
out.write_text('\n'.join(lines), encoding='utf-8')
print(out)
