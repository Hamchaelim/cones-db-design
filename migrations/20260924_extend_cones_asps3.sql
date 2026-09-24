BEGIN;

CREATE TABLE IF NOT EXISTS teams (
    team_id SERIAL PRIMARY KEY,
    team_name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE IF EXISTS users
    ADD COLUMN IF NOT EXISTS auth_user_id UUID,
    ADD COLUMN IF NOT EXISTS avatar_url TEXT,
    ADD COLUMN IF NOT EXISTS github_url TEXT,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS team_members (
    team_id INT NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (team_id, user_id)
);

ALTER TABLE IF EXISTS projects
    ADD COLUMN IF NOT EXISTS team_id INT,
    ADD COLUMN IF NOT EXISTS github_repo_id BIGINT,
    ADD COLUMN IF NOT EXISTS github_project_id BIGINT,
    ADD COLUMN IF NOT EXISTS github_project_url TEXT,
    ADD COLUMN IF NOT EXISTS repo_owner TEXT,
    ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'projects' AND c.conname = 'projects_github_repo_id_key'
    ) THEN
        ALTER TABLE projects ADD CONSTRAINT projects_github_repo_id_key UNIQUE (github_repo_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'projects' AND c.conname = 'projects_github_project_id_key'
    ) THEN
        ALTER TABLE projects ADD CONSTRAINT projects_github_project_id_key UNIQUE (github_project_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'projects' AND c.conname = 'projects_team_id_fkey'
    ) THEN
        ALTER TABLE projects ADD CONSTRAINT projects_team_id_fkey FOREIGN KEY (team_id) REFERENCES teams(team_id) ON DELETE SET NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'projects' AND c.conname = 'projects_github_repo_full_name_key'
    ) THEN
        ALTER TABLE projects ADD CONSTRAINT projects_github_repo_full_name_key UNIQUE (github_repo_full_name);
    END IF;
END $$;

ALTER TABLE IF EXISTS statuses
    ADD COLUMN IF NOT EXISTS name TEXT,
    ADD COLUMN IF NOT EXISTS position INT,
    ADD COLUMN IF NOT EXISTS is_done BOOLEAN NOT NULL DEFAULT FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_statuses_project_position ON statuses(project_id, position);
CREATE UNIQUE INDEX IF NOT EXISTS idx_statuses_project_name ON statuses(project_id, name);

ALTER TABLE IF EXISTS milestones
    ADD COLUMN IF NOT EXISTS github_milestone_number INT,
    ADD COLUMN IF NOT EXISTS title TEXT,
    ADD COLUMN IF NOT EXISTS state TEXT,
    ADD COLUMN IF NOT EXISTS due_date DATE;

CREATE UNIQUE INDEX IF NOT EXISTS idx_milestones_project_number ON milestones(project_id, github_milestone_number);

ALTER TABLE IF EXISTS tasks
    ADD COLUMN IF NOT EXISTS author_user_id INT,
    ADD COLUMN IF NOT EXISTS author_login TEXT,
    ADD COLUMN IF NOT EXISTS github_issue_id BIGINT,
    ADD COLUMN IF NOT EXISTS github_project_item_id TEXT,
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS state_reason TEXT,
    ADD COLUMN IF NOT EXISTS closed_by_user_id INT,
    ADD COLUMN IF NOT EXISTS comments_count INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS reactions JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS github_issue_payload JSONB;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'tasks' AND c.conname = 'tasks_project_id_github_issue_number_key'
    ) THEN
        ALTER TABLE tasks ADD CONSTRAINT tasks_project_id_github_issue_number_key UNIQUE (project_id, github_issue_number);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'tasks' AND c.conname = 'tasks_status_id_fkey'
    ) THEN
        ALTER TABLE tasks ADD CONSTRAINT tasks_status_id_fkey FOREIGN KEY (status_id) REFERENCES statuses(status_id) ON DELETE SET NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'tasks' AND c.conname = 'tasks_milestone_id_fkey'
    ) THEN
        ALTER TABLE tasks ADD CONSTRAINT tasks_milestone_id_fkey FOREIGN KEY (milestone_id) REFERENCES milestones(milestone_id) ON DELETE SET NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'tasks' AND c.conname = 'tasks_author_user_id_fkey'
    ) THEN
        ALTER TABLE tasks ADD CONSTRAINT tasks_author_user_id_fkey FOREIGN KEY (author_user_id) REFERENCES users(user_id) ON DELETE SET NULL;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE t.relname = 'tasks' AND c.conname = 'tasks_closed_by_user_id_fkey'
    ) THEN
        ALTER TABLE tasks ADD CONSTRAINT tasks_closed_by_user_id_fkey FOREIGN KEY (closed_by_user_id) REFERENCES users(user_id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project_id, status_id);
CREATE INDEX IF NOT EXISTS idx_tasks_project_milestone ON tasks(project_id, milestone_id);

CREATE TABLE IF NOT EXISTS task_status_history (
    history_id SERIAL PRIMARY KEY,
    task_id INT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    status_id INT REFERENCES statuses(status_id) ON DELETE SET NULL,
    changed_by_user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    note TEXT,
    raw_event JSONB
);

CREATE INDEX IF NOT EXISTS idx_task_status_history_task_changed ON task_status_history(task_id, changed_at);

CREATE TABLE IF NOT EXISTS labels (
    label_id SERIAL PRIMARY KEY,
    project_id INT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    label_name TEXT NOT NULL,
    UNIQUE (project_id, label_name)
);

CREATE TABLE IF NOT EXISTS task_labels (
    task_id INT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    label_id INT NOT NULL REFERENCES labels(label_id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, label_id)
);

CREATE TABLE IF NOT EXISTS task_comments (
    comment_id SERIAL PRIMARY KEY,
    task_id INT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    author_user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    author_login TEXT,
    body TEXT,
    comment_created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ,
    reactions JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_url TEXT,
    raw_comment JSONB
);

CREATE TABLE IF NOT EXISTS task_timeline_events (
    event_id SERIAL PRIMARY KEY,
    task_id INT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    actor_user_id INT REFERENCES users(user_id) ON DELETE SET NULL,
    actor_login TEXT,
    occurred_at TIMESTAMPTZ NOT NULL,
    raw_event JSONB,
    dedupe_key TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS task_assignees (
    task_id INT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (task_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_task_assignees_user ON task_assignees(user_id);

ALTER TABLE IF EXISTS users ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS statuses ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS milestones ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS task_assignees ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS task_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS task_comments ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS task_timeline_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS labels ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS task_labels ENABLE ROW LEVEL SECURITY;

COMMIT;
