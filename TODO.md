# TODO

Tracks implementation progress across all phases.

---

## Phase 1: Weighted Scoring MVP — COMPLETE

All Phase 1 steps are implemented, tested, and passing (`uv run pytest` → 30 passed).
Coverage: `src/scoring/` ≥ 98%, `src/constraints/` ≥ 95% (meets ≥ 90% requirement).

| Step | File(s) | Status |
|------|---------|--------|
| 1 — Data models | `src/models/{inventory,orders,movements,constraints}.py` | ✅ Done |
| 2 — WMS adapter | `src/ingestion/wms_adapter.py`, `src/ingestion/adapters/generic_db.py`, `src/ingestion/dock_schedule.py` | ✅ Done |
| 3 — Constraint engine | `src/constraints/{feasibility,temperature,hazmat,capacity}.py` | ✅ Done |
| 4 — Scoring engine | `src/scoring/{value_function,demand_predictor,weights}.py` | ✅ Done |
| 5 — Scheduler & task queue | `src/optimizer/scheduler.py`, `src/dispatch/{task_queue,agv_interface}.py` | ✅ Done |
| 6 — API layer | `src/api/main.py`, `src/api/routes/{movements,scoring,config,health}.py` | ✅ Done |
| 7 — Docker + integration tests | `docker-compose.yml`, `scripts/init_db.sql`, `tests/test_integration.py` | ✅ Done |

**Validation checklist** (from IMPLEMENTATION.md):
- [ ] SKU with confirmed order scores higher than SKU with no order — verified by `test_no_matching_order_returns_zero_score`
- [ ] Closer staging location scores higher — verified by `test_farther_from_dock_scores_higher_when_staged_closer`
- [ ] Frozen location rejects ambient SKU — verified by `test_ambient_sku_to_frozen_location_fails`
- [ ] 95% utilization drives scores down — verified by `test_utilization_at_cap_raises_opportunity_cost`
- [ ] Zero movements when no appointments — integration test covers this scenario
- [ ] Score explanations populated on all candidates — verified by `test_score_components_stored_on_candidate`
- [ ] Task expiration logic implemented — `TaskQueue.expire_old_tasks()` in `src/dispatch/task_queue.py`

---

## Phase 2: ML Demand Prediction — NOT STARTED

Replaces binary `P_load` with LightGBM probabilistic model. Gated by `use_ml_prediction` feature flag.

| Step | File(s) | Status |
|------|---------|--------|
| 8 — Feature engineering | `src/prediction/features.py` | ⬜ Not started |
| 9 — Model training | `src/prediction/trainer.py`, `scripts/generate_training_data.py` | ⬜ Not started |
| 10 — Integration with scoring | Modify `src/scoring/value_function.py` | ⬜ Not started |

**Pre-requisites:** ≥ 90 days of historical WMS data (SKU, dock_door, time_window, was_loaded label).

---

## Phase 3: OR-Based Optimization — NOT STARTED

Replaces greedy top-N dispatch with CP-SAT assignment solver + VRPTW route planner.

| Step | File(s) | Status |
|------|---------|--------|
| 11 — Assignment solver | `src/optimizer/assignment.py` | ⬜ Not started |
| 12 — Route optimization | `src/optimizer/routing.py` | ⬜ Not started |

**Pre-requisites:** Phase 1 in production with baseline metrics; OR-Tools dependency added to `pyproject.toml`.

---

## Phase 4: Reinforcement Learning — NOT STARTED

Optional. For large multi-AGV deployments where coordination is the binding constraint.

| Step | File(s) | Status |
|------|---------|--------|
| 13 — Simulation environment | `src/simulation/{warehouse_env,digital_twin,reward}.py` | ⬜ Not started |
| 14 — Training pipeline | `scripts/train_rl.py` | ⬜ Not started |

**Pre-requisites:** Phase 3 in production; accurate digital twin validated against real operations.

---

## Ongoing / Infrastructure

| Task | Status |
|------|--------|
| Calibrate weights with ops team (AHP) | ⬜ Blocked — needs human input (`scripts/calibrate_weights.py` ready) |
| Backtest on historical data | ⬜ Blocked — needs data export (`scripts/backtest.py` ready) |
| Add WebSocket `/api/v1/ws/movements` feed | ⬜ Not started (stub in API, not wired) |
| Add `src/dispatch/human_interface.py` (RF gun / tablet push) | ⬜ Not started |
| Add `src/monitoring/dashboard.py` (Grafana definitions) | ⬜ Not started |
| Kubernetes manifests (`deploy/k8s/`) | ⬜ Not started |
| Terraform (`deploy/terraform/`) | ⬜ Not started |
| Increase coverage on `src/dispatch/task_queue.py` (currently 24%) | ⬜ Not started — needs Redis test fixture |
| Increase coverage on `src/ingestion/adapters/generic_db.py` (currently 0%) | ⬜ Not started — needs DB test fixture |
