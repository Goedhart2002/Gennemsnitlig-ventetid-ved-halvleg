# Phase 7 Step-by-Step Runbook

Use this guide when you want a strict click-by-click notebook order.

## 0) Pre-check

Open a terminal in the project root and run:

```bash
source .venv/bin/activate
python scripts/verify_setup.py
```

Expected result: environment check shows all required packages as installed.

## 1) Start listeners first (do not run any Cell 5 yet)

### A. Facility manager

Open `notebooks/agent_facility_manager.ipynb` and run:

- Cell 2
- Cell 3
- Cell 4

Expected output includes:

- `Connected to MQTT broker at <host>:<port>`
- `Subscribed topic: stadium/a4/halftime/events/spectator`
- `Publish topic: stadium/a4/halftime/state/queues`
- `Subscription started. Waiting for incoming spectator events...`

### B. Congestion agent

Open `notebooks/agent_congestion.ipynb` and run:

- Cell 2
- Cell 3
- Cell 4

Expected output includes:

- `Connected to MQTT broker at <host>:<port>`
- `Subscribed topic: stadium/a4/halftime/state/queues`
- `Publish topic: stadium/a4/halftime/state/congestion`
- `Subscription started. Waiting for incoming queue-state events...`

### C. Metrics agent

Open `notebooks/agent_metrics.ipynb` and run:

- Cell 2
- Cell 3
- Cell 4

Expected output includes:

- `Connected to MQTT broker at <host>:<port>`
- `Subscribed topic: stadium/a4/halftime/events/spectator`
- `Publish topic: stadium/a4/halftime/metrics/kpi`
- `Subscription started. Waiting for incoming spectator events...`

### D. Dashboard

Open `notebooks/dashboard_a4.ipynb` and run:

- Cell 2
- Cell 3
- Cell 4

Expected output includes:

- `Connected to MQTT broker at <host>:<port>`
- `Subscribing to: stadium/a4/halftime/state/queues`
- `Subscribing to: stadium/a4/halftime/metrics/kpi`
- `Subscribing to: stadium/a4/halftime/state/congestion (optional)`
- `Dashboard callback registered.`

## 2) Prepare publisher

Open `notebooks/agent_spectator_flow.ipynb` and run:

- Cell 2
- Cell 3
- Cell 4
- Cell 5

Expected output includes:

- `Loaded halftime parameters from config.yaml:`
- `Running simulation from config...`
- `Simulation complete: <N> ticks collected`
- `Connected to MQTT broker at <host>:<port>`
- `Publish topic: stadium/a4/halftime/events/spectator`

## 3) Live overlap order (important)

Run in this order:

1. `dashboard_a4.ipynb` Cell 5 (start 30s listening window)
2. `agent_spectator_flow.ipynb` Cell 6 (publish spectator events)
3. `agent_metrics.ipynb` Cell 5 (publish final KPI)

Then run summaries:

4. `agent_spectator_flow.ipynb` Cell 7
5. `agent_facility_manager.ipynb` Cell 5
6. `agent_congestion.ipynb` Cell 5
7. `dashboard_a4.ipynb` Cell 6

## 4) Success criteria

You should see:

- Facility manager Cell 5:
  - `Received spectator events: > 0`
  - `Published queue states: > 0`
- Congestion agent Cell 5:
  - `Received queue-state events: > 0`
  - `Published congestion-state changes: >= 1`
- Dashboard Cell 6:
  - `Queue trend points: > 0`
  - `Latest KPI timestamp: 900`
  - `Average wait (s): ...`
  - `Missed kickoff count: ...`

## 5) Common mistakes

- Running Cell 5 before Cell 2 in a notebook.
  - Example failure: `NameError: name 'time' is not defined`.
  - Fix: restart kernel and run cells in order from Cell 2.

- Running listener summary cells too early.
  - If you run Cell 5 in listener notebooks before publisher cells, counts can be zero.

- Starting dashboard listening too late.
  - If dashboard Cell 5 starts after publish is finished, queue points can remain zero.

## 6) Optional validation commands

```bash
python scripts/validate_structure.py
python -m pytest
```
