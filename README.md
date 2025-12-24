```markdown
# 💹 Observability Fintech  
### Production-style Observability with Flask, Prometheus, Grafana & Loki

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](#-license)
[![Docker Compose](https://img.shields.io/badge/Docker-Compose-2496ED.svg)]()
[![Flask](https://img.shields.io/badge/Flask-2.x-000?logo=flask)]()
[![Prometheus](https://img.shields.io/badge/Prometheus-2.x-E6522C?logo=prometheus)]()
[![Grafana](https://img.shields.io/badge/Grafana-9.x-F46800?logo=grafana)]()
[![Loki](https://img.shields.io/badge/Loki-2.9-0E9A14.svg)]()

A **production-grade observability demo** for a **financial transaction service**, showcasing how **DevOps/SRE teams monitor, alert, and audit business-critical flows**.

This project simulates a fintech payments backend (Flask + Gunicorn) and instruments it end-to-end using **Prometheus, Alertmanager, Grafana, and Loki**, fully orchestrated with **Docker Compose**.

> 🎯 **Focus:** finance-relevant KPIs (TPS, error rate, p95 latency, revenue/min) and **low-noise alerting** with human + system fan-out.

---

## ✨ Why This Project Exists

This repository is intentionally **not a hello-world observability stack**.

It demonstrates how to:

- Translate **technical metrics into business KPIs**
- Design **low-noise, severity-aware alerts**
- Maintain an **auditable alert trail** using logs
- Validate dashboards and alerts with **synthetic traffic**
- Run a **full observability stack locally** using Docker

Ideal for:
- DevOps / SRE portfolios  
- Fintech observability demos  
- Interview take-home projects  
- Internal proof-of-concepts  

---

## ✨ Features

- **Application metrics** via Prometheus client (Counters, Gauges, Histograms)
- **Finance dashboard** in Grafana (TPS, Error %, Avg & p95 latency, Revenue/min)
- **Alerting** with warning/critical severity
- **Alert fan-out** to Telegram (human) + webhook (system audit)
- **Centralized logs** with Promtail → Loki
- **Infrastructure metrics** via Node Exporter & cAdvisor
- **Synthetic traffic generators** (continuous + controlled load)
- **Persistent volumes** for Prometheus, Grafana, and Loki

---

## 🧭 Architecture Overview

```

Client ──▶ Flask + Gunicorn
├─ /transaction  → business logic & metrics
├─ /metrics      → Prometheus scrape
├─ /alert        → Alertmanager webhook (audit log)
└─ JSON logs
│
▼
Promtail ──▶ Loki ──▶ Grafana (Logs)

Prometheus
├─ scrapes app & infra
├─ evaluates alert rules
└─ sends alerts ──▶ Alertmanager
├─ Telegram notifications
└─ Webhook → Flask (/alert)

Node Exporter + cAdvisor ──▶ Prometheus ──▶ Grafana (Infra)

````

---

## 📁 Repository Structure

```bash
observability-fintech
├── app/                     # Flask fintech service
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── prometheus/
│   ├── prometheus.yml
│   ├── alerts.yml
│   └── alertmanager.yml
├── grafana/
│   └── provisioning/
│       ├── dashboards/
│       └── datasources/
├── loki/config.yml
├── promtail/config.yml
├── scripts/
│   ├── loadgen.sh
│   └── load_test.py
└── docs/                    # Screenshots & diagrams (optional)
````

---

## ⚙️ Prerequisites

* Docker + Docker Compose
* Open ports: `3000, 3100, 5000, 8080, 9090, 9093, 9100`
* (Optional) Telegram bot token & chat ID

---

## 🚀 Quick Start

```bash
git clone https://gitlab.com/<you>/observability-fintech.git
cd observability-fintech

# Optional: Telegram secrets (recommended via env or .env)
export AM_TELEGRAM_BOT_TOKEN="xxxx"
export AM_TELEGRAM_CHAT_ID="123456"

docker compose up -d --build
```

### Health Checks

```bash
curl -sf localhost:5000/health && echo "APP OK"
curl -sf localhost:9090/-/ready && echo "PROM OK"
curl -sf localhost:3000/login  && echo "GRAFANA OK"
```

---

## 🌐 Service URLs

| Service      | URL                                            |
| ------------ | ---------------------------------------------- |
| Application  | [http://localhost:5000](http://localhost:5000) |
| Prometheus   | [http://localhost:9090](http://localhost:9090) |
| Alertmanager | [http://localhost:9093](http://localhost:9093) |
| Grafana      | [http://localhost:3000](http://localhost:3000) |
| Loki         | [http://localhost:3100](http://localhost:3100) |

> 🔐 Grafana default credentials: `admin / admin` — **change immediately**

---

## 📊 Metrics & Business KPIs

### Application Metrics

* `transactions_total{status}`
* `transaction_latency_seconds` (Histogram → p95)
* `transaction_amount_sum` (Revenue/min)
* `transactions_in_progress`
* `gateway_requests_total{outcome}`
* `fraud_score`

### Example PromQL Queries

```promql
# Transactions per second
sum(rate(transactions_total[1m]))

# Error rate (5m)
sum(rate(transactions_total{status="failed"}[5m])) /
clamp_min(sum(rate(transactions_total[5m])), 1e-9)

# Average latency
rate(transaction_latency_seconds_sum[5m]) /
clamp_min(rate(transaction_latency_seconds_count[5m]), 1e-9)

# p95 latency
histogram_quantile(
  0.95,
  sum by (le) (rate(transaction_latency_seconds_bucket[5m]))
)

# Revenue per minute
sum(rate(transaction_amount_sum[5m])) * 60
```

---

## 🔔 Alerting Strategy

Alerts are designed to reflect **business impact**, not metric noise.

* Warning / Critical severity levels
* Time-based confirmation using `for:` windows
* Alertmanager grouping and deduplication
* Fan-out destinations:

  * **Telegram** (human response)
  * **Webhook → Flask** (audit log in Loki)

### Alert Audit Log (LogQL)

```logql
{container="fintech_flask"} |= "alert_received"
```

---

## 🧪 Traffic & Testing

### Continuous Load (containerized)

```bash
docker logs -f loadgen
```

### Controlled Load Test

```bash
python3 scripts/load_test.py \
  --base-url http://localhost:5000 \
  --rps 12 \
  --duration 180 \
  --workers 30
```

Outputs:

* `load_output/load_summary.json`
* `load_output/load_samples.csv`

---

## 🛡️ Security & Operations Notes

* No PII or sensitive payment data in logs
* Secrets managed via environment variables or Docker secrets
* Persistent volumes for metrics and logs
* Alert webhook logs provide an **audit trail** for incidents

---

## 🗺️ Roadmap

* OpenTelemetry tracing (Jaeger / Tempo)
* Synthetic probes via Blackbox Exporter
* Kubernetes deployment (Mimir / Thanos, distributed Loki)
* CI observability smoke tests
* SLA / SLO and error budget tracking

---

## 🤝 Contributing

Contributions, issues, and suggestions are welcome.
For major changes, please open an issue to discuss first.

---

## 📄 License

This project is licensed under the **MIT License**. See `LICENSE` for details.

```

---

If you want, I can also:
- Add **screenshots placeholders** for GitLab rendering  
- Optimize this for **GitLab CI + README badges**  
- Write a **short “Demo Walkthrough” section** for interviews  

Just tell me 👍
```
