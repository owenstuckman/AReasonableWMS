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

## Phase 2 — ML Demand Prediction (SHIPPED)

| Feature | File | Status |
|---------|------|--------|
| `FeatureBuilder` — 20 features: temporal (cyclical sin/cos), SKU velocity, dock-level, order pipeline | `src/prediction/features.py` | ✅ |
| `HistoricalData` dataclass — carries demand, CV, days-since-shipment, carrier/SKU frequency | `src/prediction/features.py` | ✅ |
| `FEATURE_NAMES` canonical list — shared by training and inference to prevent drift | `src/prediction/features.py` | ✅ |
| `MLDemandPredictor.train()` — LightGBM with TimeSeriesSplit CV + Optuna 50-trial search | `src/prediction/trainer.py` | ✅ |
| `MLDemandPredictor.predict()` — isotonic-calibrated probability [0.0, 1.0] | `src/prediction/trainer.py` | ✅ |
| `MLDemandPredictor.explain()` — SHAP TreeExplainer values per feature | `src/prediction/trainer.py` | ✅ |
| `MLDemandPredictor.save()` / `load()` — pickle persistence for model + explainer | `src/prediction/trainer.py` | ✅ |
| `scale_pos_weight` class imbalance handling | `src/prediction/trainer.py` | ✅ |
| `InferenceEngine` — wraps ML predictor with circuit breaker + TTL cache + Phase 1 fallback | `src/prediction/inference.py` | ✅ |
| Circuit breaker — opens after 3 consecutive failures, half-opens after 60s recovery | `src/prediction/inference.py` | ✅ |
| Prediction cache — MD5-keyed TTL cache (default 5 min) to avoid re-computing identical inputs | `src/prediction/inference.py` | ✅ |
| `MovementScorer` ML injection — optional `ml_inference: InferenceEngine` parameter | `src/scoring/value_function.py` | ✅ |
| SHAP contributions stored as `shap_*` keys in `candidate.score_components` | `src/scoring/value_function.py` | ✅ |
| Phase 1 path preserved — no ML = binary P_load, no SHAP keys, zero behaviour change | `src/scoring/value_function.py` | ✅ |
| `ScoringContext` extended — `inventory_by_sku` and `historical_data` optional fields | `src/scoring/value_function.py` | ✅ |
| `/api/v1/scoring/explain/{id}` — now returns `shap_contributions` dict and `ml_active` flag | `src/api/routes/scoring.py` | ✅ |
| `scripts/generate_training_data.py` — `--synthetic` (dev) + `--db-url` (production) modes | `scripts/generate_training_data.py` | ✅ |

---

## Phase 3 — OR-Based Optimization (SHIPPED)

| Feature | File | Status |
|---------|------|--------|
| `StagingAssignmentSolver` — CP-SAT binary assignment maximising Σ(score × x[i][j]) | `src/optimizer/assignment.py` | ✅ |
| Assignment constraint: each candidate ≤ 1 staging location | `src/optimizer/assignment.py` | ✅ |
| Assignment constraint: each staging location ≤ 1 pallet | `src/optimizer/assignment.py` | ✅ |
| Assignment constraint: total assignments ≤ `available_resources` budget | `src/optimizer/assignment.py` | ✅ |
| Assignment constraint: temperature zone compatibility (CHILLED OK in FROZEN) | `src/optimizer/assignment.py` | ✅ |
| Assignment constraint: hazmat adjacency — incompatible DOT class pairs blocked per aisle | `src/optimizer/assignment.py` | ✅ |
| Assignment constraint: staging distance ≤ `max_staging_distance_meters` | `src/optimizer/assignment.py` | ✅ |
| Configurable solver timeout (default 10s) with best-found-so-far fallback | `src/optimizer/assignment.py` | ✅ |
| `AssignmentResult` — tasks, solver_status, objective_value, wall_seconds | `src/optimizer/assignment.py` | ✅ |
| `WarehouseGraph` — directed/undirected edges with per-edge speed zones and one-way flag | `src/optimizer/routing.py` | ✅ |
| `GraphEdge` — from/to node, distance, speed_mps, one_way | `src/optimizer/routing.py` | ✅ |
| `MovementRoutePlanner` — OR-Tools VRPTW with time-window constraints | `src/optimizer/routing.py` | ✅ |
| `Route` / `Stop` dataclasses — resource_id, ordered stops, arrival/departure times, total distance | `src/optimizer/routing.py` | ✅ |
| Manhattan distance fallback when no explicit graph edge exists | `src/optimizer/routing.py` | ✅ |
| `RoutingResult` — routes, solver_status, wall_seconds | `src/optimizer/routing.py` | ✅ |
| `SchedulerConfig.use_or_optimization` flag gates Phase 3 code path | `src/optimizer/scheduler.py` | ✅ |
| `PrePositionScheduler._run_or_cycle()` — calls CP-SAT solver, pushes assigned tasks | `src/optimizer/scheduler.py` | ✅ |
| Lazy import of solver (module loads cleanly without OR-Tools at import time) | `src/optimizer/scheduler.py` | ✅ |
| OR path increments `MOVEMENTS_DISPATCHED` Prometheus counter with `via=or_tools` tag | `src/optimizer/scheduler.py` | ✅ |

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
