import json
import os
import time
from urllib import request, error

REPO = 'seune-h0203/cones'
BASE = f'https://api.github.com/repos/{REPO}'
TOKEN = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN')
HEADERS = {
    'Accept': 'application/vnd.github+json',
    'User-Agent': 'Mozilla/5.0',
    'X-GitHub-Api-Version': '2022-11-28',
}
if TOKEN:
    HEADERS['Authorization'] = f'Bearer {TOKEN}'


def fetch_json(url: str):
    req = request.Request(url, headers=HEADERS)
    with request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def main():
    os.makedirs('data', exist_ok=True)
    repo_data = fetch_json(BASE)
    issues = []
    page = 1

    while True:
        url = f'{BASE}/issues?state=all&per_page=100&page={page}'
        batch = fetch_json(url)
        if not isinstance(batch, list) or not batch:
            break

        for issue in batch:
            if 'pull_request' in issue:
                continue

            num = issue['number']
            item = {
                'id': issue['id'],
                'number': num,
                'title': issue['title'],
                'body': issue.get('body'),
                'state': issue['state'],
                'state_reason': issue.get('state_reason'),
                'user': issue.get('user', {}).get('login') if issue.get('user') else None,
                'assignees': [a.get('login') for a in issue.get('assignees', [])],
                'milestone': issue.get('milestone', {}).get('title') if issue.get('milestone') else None,
                'milestone_number': issue.get('milestone', {}).get('number') if issue.get('milestone') else None,
                'created_at': issue.get('created_at'),
                'updated_at': issue.get('updated_at'),
                'closed_at': issue.get('closed_at'),
                'comments': issue.get('comments'),
                'reactions': issue.get('reactions', {}),
                'html_url': issue.get('html_url'),
                'labels': [l.get('name') for l in issue.get('labels', [])],
                'comments_detail': [],
                'timeline_events': [],
            }

            comments = fetch_json(f'{BASE}/issues/{num}/comments?per_page=100')
            for c in comments:
                item['comments_detail'].append({
                    'id': c['id'],
                    'user': c['user']['login'] if c.get('user') else None,
                    'body': c.get('body'),
                    'created_at': c.get('created_at'),
                    'updated_at': c.get('updated_at'),
                    'reactions': c.get('reactions', {}),
                    'html_url': c.get('html_url'),
                })

            try:
                events = fetch_json(f'{BASE}/issues/{num}/events?per_page=100')
            except error.HTTPError as exc:
                if exc.code == 410:
                    events = []
                else:
                    raise

            for ev in events:
                item['timeline_events'].append({
                    'id': ev.get('id'),
                    'event': ev.get('event'),
                    'actor': ev.get('actor', {}).get('login') if ev.get('actor') else None,
                    'created_at': ev.get('created_at'),
                    'commit_id': ev.get('commit_id'),
                    'commit_url': ev.get('commit_url'),
                    'label': ev.get('label', {}).get('name') if ev.get('label') else None,
                    'assignee': ev.get('assignee', {}).get('login') if ev.get('assignee') else None,
                    'source': ev.get('source'),
                    'raw': ev,
                })

            issues.append(item)

        if len(batch) < 100:
            break
        page += 1

    payload = {
        'repository': repo_data,
        'issues': issues,
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }

    with open('data/github-raw.json', 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f'Fetched {len(issues)} issues from {REPO}')
    print('Saved to data/github-raw.json')


if __name__ == '__main__':
    main()
