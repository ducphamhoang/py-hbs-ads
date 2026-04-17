# Notion board audit — Projects + Tasks Tracker

Generated: 2026-04-09T10:23:23.470148Z

## Executive summary
- Active projects: 11
- Active tasks: 26
- Active projects with no linked tasks: 5
- Active projects with no assignee: 1
- Active projects with Status vs Cal. Status mismatch: 6
- Active tasks with no linked project: 11
- Active tasks with no assignee: 10
- Active tasks with no due date: 22
- Active tasks flagged past due: 4
- Active tasks with weak/blank names: 4

## Active project owner load
- duc phan: 6
- Po (myntt7): 3
- DucPH: 2
- Unassigned: 1

## Active task owner load
- Unassigned: 10
- DucPH: 5
- HungCT: 3
- Po (myntt7): 3
- Kai: 3
- kieuttd2@vng.com.vn: 2
- Duong Thanh Hieu: 1
- duc phan: 1

## Sample active projects
- [CTB] V - Gỗ celshading v2 | status=In progress | cal_status=In Progress | owner=Po (myntt7) | end=2026-03-19 | tasks=0
- [AI] Improve Virtual AI Tester | status=In progress | cal_status=In Progress | owner=duc phan | end=2026-04-14 | tasks=0
- [AI]Optimize MCP CoPlay Token Usage | status=In progress | cal_status=In Progress | owner=duc phan | end=2026-04-14 | tasks=0
- How to x2 Creative Release per week | status=In progress | cal_status=Done | owner=DucPH | end=∅ | tasks=2
- Tách các pilar lớn của một video ra để chuẩn hóa | status=In progress | cal_status=Done | owner=DucPH | end=∅ | tasks=1
- [CTB] PA - Chasing Boss | status=Not started | cal_status=Done | owner=duc phan, Po (myntt7) | end=∅ | tasks=2
- [CTB] PA Pack for PvE | status=Not started | cal_status=Done | owner=duc phan | end=∅ | tasks=1
- [CTB] Phim Trường - Nghiên cứu làm giống video chuối, cacao | status=In progress | cal_status=Done | owner=duc phan | end=∅ | tasks=2
- [CTB] V -  Meme US | status=Not started | cal_status=Not Started | owner=∅ | end=∅ | tasks=0
- [CTB] V - Market Practice - DDigger | status=Not started | cal_status=Not Started | owner=Po (myntt7) | end=∅ | tasks=0

## Sample risky tasks
- Anim cho Kpop Demon Hunter | status=In progress | owner=Duong Thanh Hieu | due=2025-12-17 | linked_projects=1
- Tạo voice over (lên file excel - list) | status=Not started | owner=DucPH | due=2025-12-23 | linked_projects=1
- Danh sách video high perform | status=Not started | owner=DucPH | due=2025-12-29 | linked_projects=1
- PA MaM | status=Not started | owner=duc phan | due=2026-01-23 | linked_projects=1

## Interpretation
- The board has the right 2-level shape for media ops: Projects + Tasks Tracker.
- Main issue is hygiene inconsistency, not missing schema.
- Project-level execution state is not always trustworthy because Status and Cal. Status sometimes disagree.
- Several active projects still do not have task-level execution detail linked in.
- Several active tasks are orphaned, unassigned, undated, or too vague to manage operationally.

## Next actions
1. Choose one source of truth between Project Status and Cal. Status/rollups.
2. Enforce minimum active-task hygiene: Task name, Project, Owner, Status, Due date.
3. Standardize media-friendly execution states in Tasks Tracker, especially review/blocking states.
4. Remove/archive remaining test or low-signal active tasks.
5. After cleanup, automate a daily Scrum Master digest from this board.
