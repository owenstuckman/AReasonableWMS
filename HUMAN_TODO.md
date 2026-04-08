# Human TODO

Tasks that require manual action, real credentials, or decisions that can't be automated.
Each item states what it is, why it's needed, and exactly what to do.

---

## Before First Run

### 1. Copy and configure `.env`
**Why:** The app won't start without valid connection strings and an API key.
```bash
cd warehouse-preposition-optimizer
cp .env.example .env
# Edit .env and set:
#   DATABASE_URL — your Postgres connection string
#   REDIS_URL    — your Redis connection string
#   API_KEY      — a random secret (e.g. openssl rand -hex 32)
```

### 2. Review `config.yml` scoring weights before go-live
**Why:** Default weights are all 1.0 (equal weighting). Real operations will need tuning.
The `scripts/calibrate_weights.py` script walks through AHP pairwise comparisons interactively:
```bash
cd warehouse-preposition-optimizer
uv run python scripts/calibrate_weights.py --interactive
```
Involves: warehouse operations manager, ideally 30–60 minutes.
Output: recommended weight values to paste into `config.yml`.

### 3. Map your warehouse coordinate system
**Why:** `T_saved` and `C_move` are computed using x/y coordinates on `Location`. The current seed data uses arbitrary numbers. Real coordinates must match actual warehouse distances.
- Either update the `scripts/init_db.sql` seed with real coordinates, or
- Ensure your WMS exports x/y in meters (or feet — update `forklift_speed_mps` accordingly).

### 4. Confirm table/column names for `generic_db` adapter
**Why:** `src/ingestion/adapters/generic_db.py` assumes these table names:
  - `locations`, `skus`, `inventory_positions`, `outbound_orders`, `carrier_appointments`, `order_lines`

Your WMS database will use different names. Edit the `COLUMN_MAPPING` dict at the top of `generic_db.py` to match your schema before pointing it at a real database.

---

## Credentials & Integrations

### 5. AGV / Forklift Fleet Manager API
**Why:** `src/dispatch/agv_interface.py` is a stub that logs and returns dummy values. For real dispatching, replace it with your fleet manager's API.
- Identify fleet manager vendor (e.g., Seegrid, Fetch Robotics, Locus Robotics, or in-house)
- Obtain API credentials and endpoint documentation
- Implement the three methods: `dispatch_task()`, `get_available_resources()`, `get_resource_utilization()`

### 6. WMS read-only database user
**Why:** The adapter needs SELECT access to inventory and order tables. Never use an admin user.
```sql
CREATE USER wms_prepos_reader WITH PASSWORD 'your-password';
GRANT CONNECT ON DATABASE your_wms_db TO wms_prepos_reader;
GRANT USAGE ON SCHEMA public TO wms_prepos_reader;
GRANT SELECT ON locations, skus, inventory_positions,
                outbound_orders, carrier_appointments, order_lines
    TO wms_prepos_reader;
```

### 7. WMS adapter selection (if not using `generic_db`)
**Why:** `generic_db` works for any SQL database but requires manual column mapping. If your WMS has a REST API, it's cleaner to write a dedicated adapter.
- Check IMPLEMENTATION.md for SAP EWM, Manhattan Associates, and Blue Yonder adapter stubs
- Subclass `WMSAdapter` in `src/ingestion/wms_adapter.py`
- Set `wms.adapter: your_adapter_name` in `config.yml`

---

## Deployment

### 8. Provision Postgres and Redis
**Why:** The app needs persistent state (Postgres) and a task queue (Redis).
Recommended minimum specs for production:
- Postgres: 2 vCPU, 4 GB RAM, 50 GB SSD (mostly for historical data in Phase 2+)
- Redis: 1 vCPU, 1 GB RAM (queue + cache are small)

Docker Compose is provided for local dev / on-prem single-node:
```bash
cd warehouse-preposition-optimizer
docker compose up -d postgres redis
```
For production, use managed services (RDS + ElastiCache) or your on-prem equivalents.

### 9. Set up Prometheus + Grafana for metrics
**Why:** The app exposes `GET /api/v1/metrics` in Prometheus text format. Without a scraper you won't see queue depth, score trends, or dispatch rates.
- Point Prometheus at `http://your-app-host:8000/api/v1/metrics`
- Import the dashboard defined in `src/monitoring/dashboard.py` once implemented (see Features.md)

### 10. Configure log aggregation
**Why:** The app uses structlog (JSON output). Connect it to your log aggregator (ELK, Splunk, CloudWatch, Datadog) for operational visibility.
- Set `LOG_LEVEL=INFO` in `.env` for production (use `DEBUG` only during setup)
- Logs include: WMS poll duration, constraint violations, dispatch events, cycle timing

---

## Phase 2 Prerequisites (ML)

### 11. Export ≥ 90 days of historical WMS data
**Why:** LightGBM needs labeled training data. Required columns:
- `sku_id`, `dock_door`, `window_start`, `window_end`, `was_loaded` (0/1), plus all feature columns from `src/prediction/features.py`
- Format: CSV or direct DB table
- Minimum records: ~10,000 (sku × dock × 2hr window combinations)

Contact your WMS vendor or DBA for a data extract if this isn't already in the read-only schema.

### 12. Validate model before enabling feature flag
**Why:** The `use_ml_prediction` flag in `config.yml` replaces the binary P_load with the ML model. Don't enable it until:
- AUC-ROC ≥ 0.75 on holdout set
- Calibration curve is reasonably flat (predicted probabilities match observed frequencies)
- Run `scripts/backtest.py` to confirm ML scoring correlates with actual loading outcomes

---

## Phase 3 Prerequisites (OR)

### 13. Install Google OR-Tools
**Why:** Not included in Phase 1 dependencies to keep the install lightweight.
```bash
cd warehouse-preposition-optimizer
uv add ortools
```
Then set `optimization.enabled: true` in `config.yml`.

### 14. Build `WarehouseGraph` from your facility layout
**Why:** VRPTW route optimization needs aisle connectivity, one-way constraints, and speed zones. This data doesn't exist in a generic SQL schema.
- Export from your WMS or CAD system, or
- Build manually from warehouse floor plan (JSON format recommended)
- See `src/optimizer/routing.py` for the expected `WarehouseGraph` interface

---

## IP / Legal

### 15. Review US10504055B2 (Boston Dynamics / X Development patent)
**Why:** DESIGN.md flags this patent as potentially relevant. It covers cost-function-based layout optimization driven by shipment deadlines.
- Have legal counsel review claims 1–5 against this implementation
- Key distinguishing factor: this system is external to the WMS (different architecture); the patent describes an integrated system
- DHL's modular optimization patent establishes prior art for the external-observer pattern

---

## Operations Runbook

### 16. Define dispatch approval policy
**Why:** The system can auto-dispatch (`POST /movements/{id}/approve` is called by the scheduler) or require human approval. Decide:
- **Auto-dispatch all:** set a score threshold in `config.yml` (`min_score_threshold`)
- **Human-in-the-loop for high-value moves only:** operators review candidates via API before approving
- **Manual only:** disable auto-dispatch, operators approve via dashboard

### 17. Set task expiry window
**Why:** `scheduling.task_expiry_minutes: 15` is the default. If a PENDING task is not started within 15 minutes it auto-cancels.
Tune this based on your typical shift cycle time. Too short = excessive cancellations. Too long = stale tasks accumulate.

### 18. Define re-scoring trigger events
**Why:** The scheduler runs every 60 seconds by default (`cycle_interval_seconds: 60`). For faster response to appointment changes or new orders, you can also wire WMS event webhooks to `POST /api/v1/scheduler/trigger` (endpoint to implement).
Currently, the cycle is time-based only. Event-based triggers are a future enhancement.
