# CONES Board Architecture

## Overview

This repository models the `seune-h0203/cones` GitHub board as a normalized relational database. The design follows the original board schema in `db.spec.md`, then extends it with ASPS-3 style metadata so the project can keep richer GitHub-derived context while remaining compatible with the base task board model.

## Core design decisions

### 1. Separate board status from issue state

The schema keeps two different concepts distinct:

- `statuses.status_name` stores the kanban column such as Todo / In Progress / Done.
- `tasks.issue_state` stores whether the GitHub issue is currently open or closed.

This avoids conflating board position with issue lifecycle.

### 2. Normalize repeated entities

Users, milestones, and statuses are stored in dedicated tables instead of repeating values on each task. This reduces duplication and makes reporting easier.

### 3. Keep assignment as a relationship table

A task can have multiple assignees, and a user can be assigned to many tasks. The `task_assignees` table is therefore a proper N:M relationship with a composite primary key.

### 4. Use migration-safe extension

Existing Supabase tables were inspected before changes. We did not reset or drop the existing schema. Instead, the work was done with `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, and idempotent constraints/indexes so the project can evolve without destructive resets.

## Base schema

The canonical board schema is:

- `projects`
- `users`
- `statuses`
- `milestones`
- `tasks`
- `task_assignees`

The optional label tables were intentionally excluded from the core import because the user request specifically said to leave `labels` and `task_labels` out for now.

## Extension layer added for ASPS-3 style tracking

The existing board was extended with metadata tables and columns to support richer GitHub synchronization without breaking the original board model:

- `teams`, `team_members`
- `task_status_history`
- `task_comments`
- `task_timeline_events`
- `labels`, `task_labels` (ready for later use)
- additional GitHub metadata on `users` and `projects`

These extensions were added with constraint checks and RLS enabled on all public tables.

## Data load flow

1. Export raw GitHub issues, comments, and timeline events into `data/github-raw.json`.
2. Normalize the exported issue rows into the board schema.
3. Load in FK-safe order:
   - projects
   - users
   - statuses
   - milestones
   - tasks
   - task_assignees
4. Preserve exact issue title text without splitting prefixes such as `[QA]`, `[BE]`, `[FE]`.
5. Skip blank assignee values so only real assignee rows are inserted.

## Design change log

| Date       | Change                                                                       | Reason                                                                                                    |
| ---------- | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 2026-09-24 | Kept the original core board schema and extended it rather than replacing it | The existing Supabase project already had compatible board tables and a destructive reset would be unsafe |
| 2026-09-24 | Added ASPS-3 metadata tables and columns                                     | Needed richer GitHub issue and team context without breaking normalized board tables                      |
| 2026-09-24 | Enabled RLS on public tables                                                 | Required by the user specification for all public tables                                                  |
| 2026-09-24 | Excluded `labels` and `task_labels` from initial load                        | Explicit user requirement to defer those tables                                                           |
| 2026-09-24 | Kept exact issue titles including tag prefixes                               | Required to preserve the original board meanings                                                          |
| 2026-09-24 | Skipped empty assignee values                                                | Prevented invalid assignee rows during data import                                                        |

## Verification summary

Validated live counts in the connected Supabase project:

- `projects`: 1
- `users`: 4
- `statuses`: 3
- `milestones`: 1
- `tasks`: 19
- `task_assignees`: 26

This matches the repository board data after import while keeping the original board model intact.

## File map

- `db.spec.md`: canonical schema design
- `migrations/20260924_extend_cones_asps3.sql`: migration-safe schema extension
- `data/github-raw.json`: raw GitHub export snapshot
- `data/cones_supabase_import.sql`: generated insert script for seeded board data
- `scripts/export_github_raw.py`: GitHub export script
- `scripts/load_cones_data.py`: SQL generation script
