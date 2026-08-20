# Project Tasks and Quality Gates

| Task ID | Title | Status | Implementation State | Blockers / Gates | Document | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| T001 | Repository Baseline and Environment Setup | completed | completed | None | - | Base setup completed |
| T002 | Protocol and Serialization Specifications | completed | completed | None | - | Protocol schemas implemented |
| T003 | Map Topology and Graph Pathfinding | completed | completed | None | - | Graph navigation completed |
| T004 | Vision and Observation System | completed | completed | None | - | LOS perception completed |
| T005 | Implement Scent Model and Lock | blocked | implementation_present | OPEN-009 | [T005](tasks/T005-implement-scent-model-and-lock.md) | PR #26 merged @ 346ecfa; blocked on counted play |
| T006 | Counted Play Integration | blocked | not_started | OPEN-009 | - | Full game loop integration |
| T007 | Agent Decision and Strategy Engine | blocked | not_started | OPEN-009 | - | Strategy implementation |
| T008 | Tournament and Evaluation Harness | blocked | not_started | OPEN-009 | - | Evaluation benchmark |

## Open Gates
- **OPEN-009**: Counted play integration gate remains open until full turn simulation is wired.
