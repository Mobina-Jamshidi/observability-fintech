```markdown
# Observability Fintech (DevOps + Prometheus/Grafana/Loki)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](#-license)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED.svg)]()
[![Flask](https://img.shields.io/badge/Flask-2.x-000?logo=flask)]()
[![Prometheus](https://img.shields.io/badge/Prometheus-2.x-E6522C?logo=prometheus)]()
[![Grafana](https://img.shields.io/badge/Grafana-9.x-F46800?logo=grafana)]()
[![Loki](https://img.shields.io/badge/Loki-2.9-0E9A14.svg)]()

A complete **observability demo** for a **financial transactions service** (Flask + Gunicorn) using **Prometheus/Alertmanager**, **Grafana**, **Loki/Promtail**, **Node Exporter**, and **cAdvisor**, orchestrated with **Docker Compose**.

Focus: **finance-relevant KPIs/SLIs** (TPS, Success/Error rate, Avg/p95 latency, Revenue/min, Gateway errors, Backpressure) and **low-noise alerting** (Telegram + webhook → audit trail in logs).

---

## ✨ Features

- **App metrics** via Prometheus client (Counter/Gauge/Histogram)
- **Finance dashboard** in Grafana (TPS, status breakdown, Error%, Avg/p95 latency, Revenue/min, In-flight)
- **Alerting** (warning/critical) with **fan-out** to Telegram (human) + Flask webhook (system log trail)
- **Centralized logs** with Promtail → Loki (ready-to-use LogQL filters)
- **Infra visibility** via Node Exporter & cAdvisor
- **Traffic generator** (`loadgen.sh`) and controlled load test (`load_test.py`)
- **Persistent volumes** for Prometheus/Grafana/Loki data

---

## 🧭 Architecture

```bash

Client  →  Flask+Gunicorn (/transaction, /metrics, /alert)
│            │             │
│            │             └─ logs {"event":"alert_received"} → Loki
│            └─ Prometheus scrapes /metrics
│
loadgen  →  synthetic traffic

Node Exporter & cAdvisor → Prometheus

Prometheus (rules) ──FIRING──> Alertmanager ──┬── Telegram (human)
└── Webhook /alert (audit trail)
Grafana ← Prometheus + Loki (Dashboards & Logs)
```
---

## 📁 Repository Layout

```bash

observability-fintech
├── app/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── grafana/
│   └── provisioning/
│       ├── dashboards/
│       │   ├── dashboards.yml
│       │   ├── fintech-dashboard.json
│       │   ├── node-exporter-1860.json
│       │   └── docker-cadvisor-13496.json
│       └── datasources/
│           ├── datasource.yml
│           └── loki.yml
├── loki/config.yml
├── prometheus/
│   ├── prometheus.yml
│   ├── alerts.yml
│   └── alertmanager.yml
├── promtail/config.yml
└── scripts/
├── loadgen.sh
└── load_test.py

````

---

## ⚙️ Prerequisites

- Docker + Docker Compose
- Open ports: `3000, 3100, 5000, 8080, 9090, 9093, 9100`
- (Optional) **Telegram** bot token and chat ID for alert notifications

---

## 🚀 Quick Start

```bash
# 1) Clone
git clone https://github.com/<you>/observability-fintech.git
cd observability-fintech

# 2) (Optional) set Telegram secrets via environment or .env (recommended)
# export AM_TELEGRAM_BOT_TOKEN="xxxx"
# export AM_TELEGRAM_CHAT_ID="123456"

# 3) Up & build
docker compose up -d --build

# 4) Health checks
curl -sf localhost:5000/health && echo "APP OK"
curl -sf localhost:9090/-/ready && echo "PROM OK"
curl -sf localhost:3000/login  && echo "GRAFANA OK"
````

**URLs**

* App: [http://localhost:5000](http://localhost:5000)
* Prometheus: [http://localhost:9090](http://localhost:9090)
* Alertmanager: [http://localhost:9093](http://localhost:9093)
* Grafana: [http://localhost:3000](http://localhost:3000) (default `admin/admin`, change it)
* Loki endpoint: [http://localhost:3100](http://localhost:3100) (used via Grafana datasource)

> The Telegram route is configured in `prometheus/alertmanager.yml`. **Do not commit** real secrets—use envs or redact.

---

## 🔧 Configuration Notes

### App (Flask)

* **Endpoints**

  * `POST /transaction` — simulates payments: randomized latency, gateway errors (~5%), fraud scoring, success (~90%)
  * `GET /metrics` — Prometheus exposition
  * `POST /alert` — Alertmanager webhook → writes JSON log `{"event":"alert_received"}` (auditable in Loki)
  * `GET /health`
* **Metrics**

  * `transactions_total{status}` (Counter)
  * `transaction_latency_seconds` (Histogram → p95 via `histogram_quantile`)
  * `transaction_amount{status}` (Histogram → Revenue/min, avg ticket)
  * `transactions_in_progress` (Gauge)
  * `gateway_requests_total{outcome}`, `gateway_latency_seconds`
  * `fraud_score` (Histogram)

### Prometheus

* `prometheus.yml`: scrape every `5s`, Flask `scrape_timeout: 4s`, rules enabled via `rule_files`
* `alerts.yml`: low-noise rules with `for:` windows, `warning`/`critical`, `clamp_min()` to avoid div-by-zero

### Alertmanager

* `alertmanager.yml`: `group_by`, `group_wait`, `group_interval`, `repeat_interval`
* **Fan-out**:

  * `telegram_configs` (human notification)
  * `webhook_configs` to `http://fintech_flask:5000/alert` (system audit trail)

> **Secrets:** Never hard-code `bot_token`/`chat_id` in the repo. Use env/secrets. In public repos, redact tokens.

### Grafana

* Provisioned datasources (Prometheus, Loki) and dashboards:

  * `fintech-dashboard.json` (TPS, status breakdown, Error rate, Avg/p95 latency, Revenue/min, In-flight)
  * Node Exporter & cAdvisor community dashboards included

### Loki/Promtail (Logs)

* `promtail/config.yml` discovers Docker containers via `docker.sock`
* Labels: `container`, `service`, `stream` + parsed JSON `event`/`status`
* LogQL example (audit trail):

```logql
{container="fintech_flask"} |= "alert_received"
```

### Traffic generators

* `scripts/loadgen.sh` — continuous traffic + synthetic alert every N seconds (env-configurable)
* `scripts/load_test.py` — controlled RPS for N seconds; outputs:

  * `load_output/load_summary.json`
  * `load_output/load_samples.csv`

---

## 📊 Key Queries (PromQL/LogQL)

**PromQL**

```promql
# TPS
sum(rate(transactions_total[1m]))

# Success/Total (5m)
sum(rate(transactions_total{status="success"}[5m])) /
clamp_min(sum(rate(transactions_total[5m])), 1e-9)

# Error/Total (5m)
sum(rate(transactions_total{status="failed"}[5m])) /
clamp_min(sum(rate(transactions_total[5m])), 1e-9)

# Avg latency (5m)
rate(transaction_latency_seconds_sum[5m]) /
clamp_min(rate(transaction_latency_seconds_count[5m]), 1e-9)

# p95 latency (5m)
histogram_quantile(0.95, sum by (le)(rate(transaction_latency_seconds_bucket[5m])))

# Revenue/min (5m)
sum(rate(transaction_amount_sum[5m])) * 60

# Gateway error share (5m)
sum(rate(gateway_requests_total{outcome="error"}[5m])) /
clamp_min(sum(rate(gateway_requests_total[5m])), 1e-9)

# Backpressure (instant)
transactions_in_progress
```

**LogQL**

```logql
# Alert audit trail
{container="fintech_flask"} |= "alert_received"
```

---

## 🔔 Alerts (samples)

* **HighErrorRate** / **HighErrorRateCritical**
* **HighLatencyP95** / **HighLatencyP95Critical**
* **HighLatencyAvg** / **HighLatencyAvgCritical**
* **HighGatewayErrorRate** / **...Critical**
* **HighFraudRate** / **...Critical**
* **RevenueDrop**
* **Backpressure** / **BackpressureCritical**

Design principles: `for:` windows (2–10m), severity separation (warning/critical), Alertmanager grouping to reduce noise.

---

## 🛡️ Security & Ops Notes

* **No PII in logs**; only operational events (e.g., `alert_received`)
* **Secrets** (Telegram) via env/secret files; **never** commit real tokens
* Grafana: change default password, enable RBAC; restrict management ports or use TLS reverse proxy
* Persistent volumes: `prometheus-data`, `grafana-data`, `loki-data`
* Consider retention/backup policies for long-running setups

---

## 🧪 Testing

**Continuous load (containerized)**

```bash
docker logs -f loadgen
```

**Controlled local test**

```bash
python3 scripts/load_test.py --base-url http://localhost:5000 --rps 12 --duration 180 --workers 30
cat load_output/load_summary.json
```

---

## ❓ Troubleshooting

* **Prometheus exits**: check `docker logs prometheus`

  * Ensure `scrape_timeout < scrape_interval`
* **Alertmanager YAML error**: type correctness (e.g., numeric `chat_id`)
* **No logs in Grafana**: verify Loki datasource, Promtail discovery; try:

  ```logql
  {container="fintech_flask"}
  ```
* **Alert noise**: increase `for:` windows or adjust `group_wait/group_interval/repeat_interval`

---

## 🗺️ Roadmap

* Secrets via `.env` / Docker secrets
* Synthetic probes (blackbox_exporter)
* Tracing (Jaeger/OTel) for multi-service scenarios
* K8s + Thanos/Mimir + distributed Loki for HA/scale
* CI/CD lint for YAML + post-deploy observability smoke tests

---

## 🤝 Contributing

PRs and issues are welcome. For substantial changes, please open an issue first to discuss what you would like to change.

---

## 📄 License

This project is licensed under the **MIT License**. See `LICENSE` for details.

---

## 📦 Extras to include in the repo

* `docs/` folder with screenshots:

  * `architecture.png`, `tree.png`, `docker-ps.png`, `prom-targets.png`, `prom-alerts.png`, `grafana-fintech.png`, `grafana-logs.png`, `alertmanager.png`, `telegram.png`, `load-summary.png`
* A `LICENSE` file (MIT recommended)
* Optional `.env.example`:

  ```env
  # Alertmanager → Telegram
  AM_TELEGRAM_BOT_TOKEN=REDACTED
  AM_TELEGRAM_CHAT_ID=123456789
  ```
