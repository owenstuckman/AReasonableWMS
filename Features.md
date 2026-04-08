# Features

Tracks every feature by phase, status, and the file(s) that implement it.

---

## Phase 1 — Weighted Scoring MVP (SHIPPED)

### Data Layer
| Feature | File | Status |
|---------|------|--------|
| `Location` model (zone, aisle, bay, temp zone, capacity, staging flag, dock door) | `src/models/inventory.py` | ✅ |
| `SKU` model (weight, volume, hazmat class, temp requirement, ABC class) | `src/models/inventory.py` | ✅ |
| `InventoryPosition` model (SKU + location + quantity + lot/expiry) | `src/models/inventory.py` | ✅ |
| `CarrierAppointment` model (dock door, arrival/departure, status enum) | `src/models/orders.py` | ✅ |
| `OutboundOrder` + `OrderLine` models | `src/models/orders.py` | ✅ |
| `CandidateMovement` model (score, score_components, reason) | `src/models/movements.py` | ✅ |
| `MovementTask` model (status enum, dispatched_at, completed_at) | `src/models/movements.py` | ✅ |
| `FeasibilityResult` + `ConstraintViolation` models | `src/models/constraints.py` | ✅ |
| `WarehouseState` bundle (inventory + orders + appointments + staging + utilization) | `src/ingestion/wms_adapter.py` | ✅ |

### Ingestion
| Feature | File | Status |
|---------|------|--------|
| Abstract `WMSAdapter` interface (5 async methods) | `src/ingestion/wms_adapter.py` | ✅ |
| `GenericDatabaseAdapter` — polls PostgreSQL, maps columns to models | `src/ingestion/adapters/generic_db.py` | ✅ |
| Redis caching layer (configurable TTL, default 60s) | `src/ingestion/adapters/generic_db.py` | ✅ |
| `DockScheduleIngester` — filters active appointments, sorts by arrival | `src/ingestion/dock_schedule.py` | ✅ |
| Structlog metrics on poll duration and record counts | `src/ingestion/adapters/generic_db.py` | ✅ |

### Constraint Engine
| Feature | File | Status |
|---------|------|--------|
| `ConstraintFilter` ABC (pluggable hard/soft constraint pattern) | `src/constraints/feasibility.py` | ✅ |
| `FeasibilityEngine` — stops on first HARD violation, collects SOFT | `src/constraints/feasibility.py` | ✅ |
| Temperature constraint — AMBIENT/CHILLED/FROZEN zone enforcement | `src/constraints/temperature.py` | ✅ |
| Temperature exception — CHILLED SKU allowed in FROZEN zone | `src/constraints/temperature.py` | ✅ |
| Hazmat segregation — DOT incompatible class pairs blocked per bay | `src/constraints/hazmat.py` | ✅ |
| Capacity constraint — weight and volume utilization check (≤ 95%) | `src/constraints/capacity.py` | ✅ |

### Scoring Engine
| Feature | File | Status |
|---------|------|--------|
| `ScoringWeights` Pydantic model (5 terms + decay constant) | `src/scoring/weights.py` | ✅ |
| V(m) = (T_saved × P_load × W_order) / (C_move + C_opportunity) | `src/scoring/value_function.py` | ✅ |
| T_saved — Manhattan distance delta to dock in seconds | `src/scoring/value_function.py` | ✅ |
| P_load — Phase 1 binary lookup (SKU on order for appointment) | `src/scoring/demand_predictor.py` | ✅ |
| W_order — priority × exp(−time_to_cutoff / decay_constant), clamped [0.1, 10.0] | `src/scoring/value_function.py` | ✅ |
| C_move — travel time + 45s handling time | `src/scoring/value_function.py` | ✅ |
| C_opportunity — base × 1/(1 − util), clamped at util=0.95 | `src/scoring/value_function.py` | ✅ |
| Score components stored on `CandidateMovement` for API explainability | `src/scoring/value_function.py` | ✅ |
| Short-circuit: returns 0.0 when T_saved ≤ 0 or P_load = 0 | `src/scoring/value_function.py` | ✅ |

### Scheduling & Dispatch
| Feature | File | Status |
|---------|------|--------|
| `PrePositionScheduler.generate_candidates()` — full pipeline (fetch → generate → filter → score → dedup → top-N) | `src/optimizer/scheduler.py` | ✅ |
| Staging location selection — prefer dock-matched, fall back to nearest by distance | `src/optimizer/scheduler.py` | ✅ |
| SKU deduplication — keep highest-scored movement per SKU | `src/optimizer/scheduler.py` | ✅ |
| `PrePositionScheduler.dispatch_top_movements()` — converts to tasks, pushes to queue | `src/optimizer/scheduler.py` | ✅ |
| `PrePositionScheduler.run_cycle()` — full generate + dispatch cycle | `src/optimizer/scheduler.py` | ✅ |
| Redis-backed `TaskQueue` — sorted set by score, hash for task data | `src/dispatch/task_queue.py` | ✅ |
| Task expiry — PENDING tasks auto-cancelled after configurable window (default 15 min) | `src/dispatch/task_queue.py` | ✅ |
| Status transitions: PENDING → IN_PROGRESS → COMPLETED / CANCELLED | `src/dispatch/task_queue.py` | ✅ |
| `AGVInterface` stub — placeholder for real fleet manager API | `src/dispatch/agv_interface.py` | ✅ |

### API
| Feature | File | Status |
|---------|------|--------|
| `GET /api/v1/movements/candidates` — scored candidate list | `src/api/routes/movements.py` | ✅ |
| `POST /api/v1/movements/{id}/approve` — dispatch a candidate | `src/api/routes/movements.py` | ✅ |
| `POST /api/v1/movements/{id}/reject` — reject with reason | `src/api/routes/movements.py` | ✅ |
| `GET /api/v1/movements/active` — active task list | `src/api/routes/movements.py` | ✅ |
| `GET /api/v1/scoring/explain/{id}` — score component breakdown | `src/api/routes/scoring.py` | ✅ |
| `GET /api/v1/config/weights` — read current weights | `src/api/routes/config.py` | ✅ |
| `PUT /api/v1/config/weights` — update weights at runtime | `src/api/routes/config.py` | ✅ |
| `GET /api/v1/health` — system health (WMS, Redis, queue depth) | `src/api/routes/health.py` | ✅ |
| `GET /api/v1/metrics` — Prometheus text format | `src/api/routes/health.py` | ✅ |
| API key auth (`X-API-Key` header) | `src/api/main.py` | ✅ |
| CORS middleware | `src/api/main.py` | ✅ |
| Request logging via structlog | `src/api/main.py` | ✅ |
| Lifespan handler — initializes scheduler, queue, WMS adapter | `src/api/main.py` | ✅ |

### Observability
| Feature | File | Status |
|---------|------|--------|
| Prometheus metrics: `movements_scored_total`, `movements_dispatched_total`, `movements_completed_total` | `src/monitoring/metrics.py` | ✅ |
| Prometheus metrics: `avg_score`, `queue_depth`, `wms_poll_duration_seconds`, `constraint_violations_total` | `src/monitoring/metrics.py` | ✅ |

### Infrastructure
| Feature | File | Status |
|---------|------|--------|
| Docker Compose (Postgres 16, Redis 7, app) | `docker-compose.yml` | ✅ |
| DB seed script (100 locations, 50 SKUs, 10 orders, 4 appointments) | `scripts/init_db.sql` | ✅ |
| Dockerfile | `Dockerfile` | ✅ |
| `scripts/calibrate_weights.py` — AHP weight calibration wizard | `scripts/calibrate_weights.py` | ✅ |
| `scripts/backtest.py` — historical score correlation analysis | `scripts/backtest.py` | ✅ |
| Config file (`config.yml`) with all tunable parameters | `config.yml` | ✅ |
| Pydantic Settings loading from env + YAML | `src/config.py` | ✅ |
| Feature flags: `use_ml_prediction`, `use_or_optimization` | `src/config.py` | ✅ |

---

## Phase 2 — ML Demand Prediction (NOT STARTED)

| Feature | File | Status |
|---------|------|--------|
| `FeatureBuilder` — 17 features across temporal / SKU / dock / order pipeline dimensions | `src/prediction/features.py` | ⬜ |
| `DemandPredictor.train()` — LightGBM with TimeSeriesSplit + Optuna hyperparameter search | `src/prediction/trainer.py` | ⬜ |
| `DemandPredictor.predict()` — calibrated probability [0.0, 1.0] | `src/prediction/trainer.py` | ⬜ |
| `DemandPredictor.explain()` — SHAP values per feature | `src/prediction/trainer.py` | ⬜ |
| `DemandPredictor.inference()` — real-time serving with circuit breaker | `src/prediction/inference.py` | ⬜ |
| Training data generator script | `scripts/generate_training_data.py` | ⬜ |
| SMOTE / class_weight for imbalanced labels | `src/prediction/trainer.py` | ⬜ |
| Feature flag integration in scorer (`use_ml_prediction`) | `src/scoring/value_function.py` | ⬜ |
| SHAP contributions surfaced in score explanations | `src/api/routes/scoring.py` | ⬜ |

---

## Phase 3 — OR-Based Optimization (NOT STARTED)

| Feature | File | Status |
|---------|------|--------|
| `StagingAssignmentSolver` — CP-SAT assignment (maximize total value) | `src/optimizer/assignment.py` | ⬜ |
| Assignment constraints: capacity, temp zone, hazmat adjacency, max staging distance | `src/optimizer/assignment.py` | ⬜ |
| 10s solver timeout with best-found fallback | `src/optimizer/assignment.py` | ⬜ |
| `MovementRoutePlanner` — VRPTW for forklift/AGV sequencing | `src/optimizer/routing.py` | ⬜ |
| `WarehouseGraph` — aisle connectivity, one-way aisles, speed zones | `src/optimizer/routing.py` | ⬜ |
| Feature flag integration (`use_or_optimization`) | `src/optimizer/scheduler.py` | ⬜ |
| OR-based fallback policy for Phase 4 RL agent | `src/optimizer/scheduler.py` | ⬜ |

---

## Phase 4 — Reinforcement Learning (NOT STARTED)

| Feature | File | Status |
|---------|------|--------|
| `WarehousePrePositionEnv` — Gymnasium env wrapping SimPy DES | `src/simulation/warehouse_env.py` | ⬜ |
| `WarehouseDigitalTwin` — SimPy discrete-event warehouse simulation | `src/simulation/digital_twin.py` | ⬜ |
| Reward function (time saved, movement cost, dock departure bonus/penalty) | `src/simulation/reward.py` | ⬜ |
| Action masking — prevent infeasible actions at Gymnasium level | `src/simulation/warehouse_env.py` | ⬜ |
| Single-agent PPO prototype (Stable Baselines3) | `scripts/train_rl.py` | ⬜ |
| Multi-agent MAPPO production (Ray RLlib) | `scripts/train_marl.py` | ⬜ |
| Domain randomization for sim-to-real transfer | `src/simulation/warehouse_env.py` | ⬜ |
| ONNX export for production inference | `scripts/export_onnx.py` | ⬜ |

---

## Deferred (Out of Scope for Current Phases)

| Feature | Notes |
|---------|-------|
| SAP EWM adapter | Needs SAP RFC credentials and `pyrfc` library |
| Manhattan Associates adapter | Needs API credentials |
| Blue Yonder adapter | Needs API credentials |
| `src/dispatch/human_interface.py` — RF gun / tablet task push | WMS-specific integration |
| WebSocket `/api/v1/ws/movements` real-time feed | Stub present in routes, not wired |
| `src/monitoring/dashboard.py` — Grafana dashboard JSON | Needs Grafana deployment |
| Kubernetes manifests (`deploy/k8s/`) | Post-containerization |
| Terraform (`deploy/terraform/`) | Post-containerization |
