# Human TODO

Tasks that require manual action, real credentials, external decisions, or operational setup that code cannot do on its own. Each item states what it is, why it's needed, and exactly what to do.

Items are numbered sequentially. Sections are ordered by when you need to act.

---

## A. Before First Run (Blocking)

### 1. Copy and configure `.env`
**Why:** The app won't start without valid connection strings and an API key.
```bash
cd warehouse-preposition-optimizer
cp .env.example .env
# Edit .env:
#   DATABASE_URL — postgresql+asyncpg://user:pass@host:5432/dbname
#   REDIS_URL    — redis://host:6379/0
#   API_KEY      — random secret: openssl rand -hex 32
```

### 2. Map real warehouse coordinates into Location x/y
**Why:** `T_saved` and `C_move` are computed from `Location.x` and `Location.y` in meters. The seed data uses arbitrary numbers. Wrong coordinates = wrong scores.
- Option A: Update `scripts/init_db.sql` seed rows with real x/y from your CAD or WMS floor plan.
- Option B: Ensure your WMS exports x/y in meters; update `forklift_speed_mps` in `config.yml` if your WMS uses feet.
- **Also map dock door coordinates**: `src/scoring/value_function._dock_door_coords()` currently uses a placeholder (`door * 5m`). Replace with real values, or move dock door positions into the `locations` table and fetch them from the WMS adapter.

### 3. Map real dock door x/y coordinates
**Why:** The scoring function's `T_saved` term measures distance to the dock door. The placeholder `_dock_door_coords(door_id)` returns `(0.0, door * 5.0)`. This makes distance calculations approximate at best.
- Add a `dock_doors` table to `scripts/init_db.sql` with real x/y per door, or
- Add a `dock_door_coordinates: dict[int, tuple[float, float]]` config section to `config.yml`, or
- Modify `GenericDBAdapter` to query dock door positions from the WMS `locations` table where `is_staging=false AND nearest_dock_door IS NOT NULL`.

### 4. Confirm table/column names for `generic_db` adapter
**Why:** `src/ingestion/adapters/generic_db.py` assumes specific table and column names. Your WMS schema will differ.
- Edit the `COLUMN_MAPPING` dict near the top of `generic_db.py` to match your schema.
- Expected tables: `locations`, `skus`, `inventory_positions`, `outbound_orders`, `carrier_appointments`, `order_lines`.
- Test the mapping with a dry-run against a read-only copy of the WMS DB before pointing at production.

---

## B. Credentials & Integrations (Blocking for Production)

### 5. Create WMS read-only database user
**Why:** The adapter needs `SELECT` on inventory/order tables. Never use an admin credential.
```sql
CREATE USER wms_prepos_reader WITH PASSWORD 'strong-random-password';
GRANT CONNECT ON DATABASE your_wms_db TO wms_prepos_reader;
GRANT USAGE ON SCHEMA public TO wms_prepos_reader;
GRANT SELECT ON
    locations, skus, inventory_positions,
    outbound_orders, carrier_appointments, order_lines
    TO wms_prepos_reader;
-- Revoke write access explicitly if inherited from a role:
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM wms_prepos_reader;
```

### 6. Replace the AGV/forklift fleet manager stub
**Why:** `src/dispatch/agv_interface.py` is a placeholder. `dispatch_task()` always returns `True`, `get_resource_utilization()` always returns `0.0`. No tasks actually reach physical equipment.
- Identify your fleet manager vendor (Seegrid, Fetch Robotics, Locus Robotics, MiR, or in-house TMS).
- Obtain API credentials, endpoint docs, and task payload schema.
- Implement the three methods: `dispatch_task()`, `get_available_resources()`, `get_resource_utilization()`.
- `get_resource_utilization()` is used as input to `C_opportunity`. Without a real value, the system can't detect when forklifts are overloaded.

### 7. WMS adapter selection (if not using `generic_db`)
**Why:** `generic_db` works for any SQL DB but requires manual column mapping. If your WMS exposes a REST or EWM API, a dedicated adapter is cleaner.
- Subclass `WMSAdapter` in `src/ingestion/wms_adapter.py`.
- Set `wms.adapter: your_adapter_name` in `config.yml`.
- Reference adapters in `IMPLEMENTATION.md` for SAP EWM, Manhattan Associates, Blue Yonder patterns.

---

## C. Deployment

### 8. Provision Postgres and Redis
**Why:** The app requires both for startup. Without Postgres the WMS adapter fails on connect; without Redis the task queue silently degrades.

Minimum production specs:
| Service | vCPU | RAM | Storage | Notes |
|---------|------|-----|---------|-------|
| Postgres | 2 | 4 GB | 50 GB SSD | Grows with historical data for Phase 2 |
| Redis | 1 | 1 GB | — | Queue + cache; < 100 MB typical |

Docker Compose (local dev / on-prem single-node):
```bash
cd warehouse-preposition-optimizer
docker compose up -d postgres redis
```

For production use managed services (AWS RDS + ElastiCache, GCP Cloud SQL + Memorystore) or on-prem HA equivalents.

### 9. Restrict CORS for production
**Why:** `src/api/main.py` currently sets `allow_origins=["*"]`. This is intentional for development but must be restricted in production to prevent cross-origin access from untrusted domains.
- Add `CORS_ORIGINS=https://your-dashboard.internal,https://ops.example.com` to `.env`.
- Update `main.py` to read `allow_origins` from settings instead of hardcoding `["*"]`.

### 10. Set up TLS termination
**Why:** The API key travels in the `X-API-Key` header. Without TLS, it's visible in transit.
- Use a reverse proxy (nginx, Caddy, AWS ALB) to terminate TLS in front of the app.
- The app itself listens on port 8000 HTTP; do not expose port 8000 directly.

### 11. Build and push Docker image
**Why:** `docker-compose.yml` builds from `./Dockerfile` locally. For deployments beyond a single dev machine, you need a registry.
```bash
docker build -t warehouse-prepos:0.1.0 .
docker tag warehouse-prepos:0.1.0 your-registry/warehouse-prepos:0.1.0
docker push your-registry/warehouse-prepos:0.1.0
```

### 12. Set up Prometheus + Grafana for metrics
**Why:** The app exposes `GET /api/v1/metrics` in Prometheus text format. Queue depth, score trends, and dispatch rates are invisible without a scraper.
- Point a Prometheus scrape job at `http://app-host:8000/api/v1/metrics`, interval 15s.
- Import or create a Grafana dashboard for: queue_depth, movements_dispatched_total, avg_score, wms_poll_duration_seconds, constraint_violations_total.
- Prometheus counters are fully wired: `MOVEMENTS_SCORED`, `MOVEMENTS_DISPATCHED`, `MOVEMENTS_COMPLETED`, `QUEUE_DEPTH`, `AVG_SCORE`, `CONSTRAINT_VIOLATIONS` are all incremented correctly.

### 13. Configure log aggregation
**Why:** The app uses structlog (JSON output). Raw stdout is lost on container restart without a collector.
- Set `LOG_LEVEL=INFO` in `.env` for production.
- Ship logs to ELK, Splunk, Datadog, or CloudWatch via your container runtime's log driver.
- Key log events to alert on: `ml_circuit_opened`, `scheduler_loop.cycle_error`, `app.wms_unavailable`.

### 14. Set up operational alerts
**Why:** Failures are logged but don't page anyone by default. Critical signals:

| Alert | Condition | Urgency |
|-------|-----------|---------|
| Scheduler not cycling | No `scheduler_loop.cycle_done` log in > 3× `cycle_interval_seconds` | High |
| WMS disconnected | `app.wms_unavailable` at startup or poll | High |
| ML circuit open | `ml_circuit_opened` log event | Medium |
| Queue depth spike | `queue_depth` > 2× `dispatch_batch_size` for > 5 min | Medium |
| Constraint violations rate | `constraint_violations_total` > 20% of candidates scored | Low (monitoring) |

---

## D. Calibration (Affects Score Quality)

### 15. Calibrate scoring weights with ops team (AHP)
**Why:** Default weights are all 1.0 (equal). Ops managers have domain knowledge about which terms matter most for your specific facility and carrier mix.

The `calibrate_weights.py` script walks through AHP pairwise comparisons interactively:
```bash
cd warehouse-preposition-optimizer
uv run python scripts/calibrate_weights.py --interactive
```
Budget 30–60 minutes with a warehouse operations manager.
Output: recommended weight values — paste into `config.yml` under `scoring.weights`.

### 16. Define dispatch approval policy
**Why:** The system can auto-dispatch everything above `min_score_threshold`, require human approval for all moves, or hybrid. This is an operational decision.

| Mode | Config | When to use |
|------|--------|-------------|
| Auto-dispatch all | `min_score_threshold: 0.1` (default) | High-trust, high-volume operations |
| Human-in-the-loop | Remove auto-dispatch, operators approve via `/movements/{id}/approve` | Initial rollout, audit requirements |
| Threshold-gated | Raise `min_score_threshold` to filter low-confidence moves | After backtesting establishes good score baseline |

### 17. Set task expiry window
**Why:** `scheduling.task_expiry_minutes: 15` is the default. Tasks not started within this window auto-cancel. Too short → excessive re-scoring churn. Too long → stale moves execute after conditions change.
- Tune to your typical cycle time: `expiry_minutes ≈ 2 × avg_forklift_cycle_minutes`.

---

## E. Phase 2: ML Activation (Code Complete, Data Required)

### 18. Export ≥ 90 days of historical WMS data
**Why:** LightGBM needs labelled training data. All code is ready; only the data is missing.

Verify the pipeline first with synthetic data:
```bash
cd warehouse-preposition-optimizer
uv run python scripts/generate_training_data.py --synthetic --rows 20000 --out data/training.csv
```

For real training data:
```bash
uv run python scripts/generate_training_data.py \
    --db-url postgresql+psycopg2://user:pass@host/wms_db \
    --start-date 2024-01-01 --end-date 2024-03-31 \
    --out data/training.csv
```

Required: all 20 columns from `src/prediction/features.FEATURE_NAMES` plus `was_loaded` (0/1).
Minimum: ~10,000 rows. Aim for 50,000+ for reliable AUC.

### 19. Train and save the ML model
**Why:** `MLDemandPredictor` is fully implemented but has no saved artifact yet.

```python
# Run from the warehouse-preposition-optimizer/ directory:
import pandas as pd
from src.prediction.trainer import MLDemandPredictor

df = pd.read_csv("data/training.csv")
model = MLDemandPredictor()
metrics = model.train(df, n_trials=50, cv_folds=5)
print(metrics)   # inspect cv_auc_mean — must be ≥ 0.75 before enabling
model.save("models/demand_lgbm.pkl")
```

### 20. Validate model before enabling the feature flag
**Why:** The `prediction.enabled: true` flag switches P_load from binary lookup to ML. Bad model = bad scores = wrong moves.
- AUC-ROC on holdout ≥ 0.75 (reported by `train()` metrics).
- Run `scripts/backtest.py` to confirm ML scores correlate with actual loading outcomes.
- Compare: same appointments, Phase 1 scores vs Phase 2 scores. Review anomalies with ops team.
- Once satisfied: in `config.yml` set `prediction.enabled: true` and `prediction.model_path: models/demand_lgbm.pkl`.

### 21. Mount model artifact in Docker
**Why:** The `models/` directory is in `.gitignore` and won't be in the Docker image. The lifespan handler will log a warning and fall back to Phase 1 if the file is missing.
- Option A: Build a separate model image layer (`COPY models/ /app/models/`).
- Option B: Mount a volume: `docker run -v /path/to/models:/app/models ...`.
- Option C: Download from S3/GCS at container startup (add an init script).

### 22. Populate `carrier_id_encoding` and `carrier_sku_frequency` in HistoricalData
**Why:** These two fields in `HistoricalData` default to 0 if not populated. They're among the stronger ML features. Populate them from your historical order data.

```python
# Build from historical shipment records:
hist = HistoricalData(
    carrier_id_encoding={"FedEx": 0, "UPS": 1, "ACME": 2, ...},
    carrier_sku_frequency={("FedEx", "SKU-001"): 0.42, ...},
    avg_daily_demand={"SKU-001": 35.0, ...},
    # ...
)
```
Persist this as a JSON file and load it at startup alongside the model artifact.

---

## F. Phase 3: OR-Tools Activation (Code Complete)

OR-Tools is already installed (`ortools>=9.15.6755` in `pyproject.toml`). The CP-SAT assignment solver (`src/optimizer/assignment.py`) and VRPTW route planner (`src/optimizer/routing.py`) are implemented and all 27 Phase 3 tests pass. The following items are operational decisions and data tasks.

### 23. Enable Phase 3 in config
**Why:** The feature flag `optimization.enabled` is `false` by default. The code is ready; the flag just needs to be flipped once Phase 1 baseline metrics are collected.

In `config.yml`:
```yaml
optimization:
  enabled: true
  solver_timeout_seconds: 10   # raise to 30 for large cycles (>100 candidates)
  route_optimization: true
```

Also set the resource budget in `config.yml` or the equivalent env var. The `available_resources` value (default 5) is the max simultaneous movements the CP-SAT solver is allowed to select per cycle. Match this to your actual available fleet count.

### 24. Build `WarehouseGraph` from facility layout
**Why:** VRPTW route optimization needs aisle connectivity, one-way aisle constraints, and speed zones. The fallback is Manhattan distance, which over- or under-estimates travel time near narrow aisles or around obstacles.

- Option A: Export from WMS/WCS CAD/BIM system as GeoJSON or adjacency list.
- Option B: Build manually from warehouse floor plan. Recommended format: JSON adjacency list with speed and direction attributes per edge.

Wire the graph at startup in `src/api/main.py`:
```python
from src.optimizer.routing import WarehouseGraph, GraphEdge
g = WarehouseGraph(default_speed_mps=2.2)
g.add_edge(GraphEdge("LOC-A", "LOC-B", distance_meters=12.5, speed_mps=2.0))
# ... one edge per aisle segment
app.state.warehouse_graph = g
```

Pass `warehouse_graph` to `MovementRoutePlanner(graph=g)` inside the scheduler.
Validate: shortest path from any location to any dock door should match actual forklift travel times within ±15%.

### 25. Establish Phase 1 production baseline before enabling Phase 3
**Why:** The CP-SAT solver objective is "maximize total value." Without real historical V(m) data, there's no way to know if the OR solution is better than greedy top-N. Collect at least 2 weeks of:
- Movements scored and dispatched per cycle.
- Dock dwell times (truck arrival → departure).
- Pre-stage hit rate (loads from staging / total loads).
- Movement ROI (total time saved / total movement cost). Target: > 2.0.

---

## G. IP / Legal

### 26. Review US10504055B2 (Boston Dynamics / X Development patent)
**Why:** DESIGN.md flags this as potentially relevant. It covers cost-function-based layout optimization driven by shipment deadlines and robotic execution.
- Have legal counsel review claims 1–5.
- Key distinguishing factors: (1) this system is external to the WMS — the patent describes integrated WMS architecture; (2) DHL's modular optimization patent establishes prior art for the external-observer pattern.
- If counsel identifies overlap, consider documenting design decisions that distinguish this implementation.

---

## H. Ongoing Operations

### 27. Define and test rolling restart procedure
**Why:** Restarting the app cancels the background scheduler loop and briefly loses Redis connection. Tasks in PENDING state survive (they're in Redis), but the timing window matters.
- Procedure: drain queue (`GET /api/v1/movements/active`), wait for IN_PROGRESS tasks to complete, then restart.
- Document: how to drain, max acceptable restart time, and Redis TTL interaction.

### 28. Back up Redis task state
**Why:** Redis is used as the task queue. Without backups, a Redis restart loses all PENDING task metadata. Active tasks in progress are at risk.
- Enable Redis persistence (`appendonly yes`) for the task queue instance, or
- Use a separate Redis instance with persistence for tasks vs. the caching instance.
- Schedule daily `SAVE` or use RDB snapshots.

### 29. Define re-scoring trigger events
**Why:** The scheduler runs automatically every `cycle_interval_seconds` (default: 60s). For faster response to appointment changes or new high-priority orders, wire event-based triggers.
- Planned endpoint: `POST /api/v1/scheduler/trigger` (not yet implemented — see TODO.md).
- Can be called by WMS webhooks, appointment check-in events, or task completion callbacks.
