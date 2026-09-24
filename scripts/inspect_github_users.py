import json
from pathlib import Path

p = Path('data/github-raw.json')
obj = json.loads(p.read_text(encoding='utf-8'))
users = set()
for issue in obj['issues']:
    if issue.get('user'):
        users.add(issue['user'])
    for a in issue.get('assignees', []):
        if a:
            users.add(a)
print(sorted(users))
print('count=', len(users))
