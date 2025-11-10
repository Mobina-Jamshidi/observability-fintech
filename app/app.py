from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import random
import time
import json
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# --- Core app metrics ---
TRANSACTION_COUNT = Counter(
    'transactions_total', 'Total processed transactions', ['status']
)

# Use Histogram for latency to enable p90/p95 with histogram_quantile
TRANSACTION_LATENCY = Histogram(
    'transaction_latency_seconds', 'Transaction processing time in seconds',
    buckets=[0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0, float("inf")]
)

# Transaction amount by outcome; enables revenue, avg ticket, distribution
TRANSACTION_AMOUNT = Histogram(
    'transaction_amount', 'Transaction amount by status',
    ['status'],
    buckets=[10, 50, 100, 250, 500, 1000, 2000, 5000, float("inf")]
)

# In-flight gauge to visualize concurrency/backpressure
TRANSACTION_IN_PROGRESS = Gauge(
    'transactions_in_progress', 'Current transactions being processed'
)

# --- Simulated dependency (e.g., payment gateway) ---
GATEWAY_REQUESTS = Counter(
    'gateway_requests_total', 'Simulated payment gateway requests', ['outcome']  # outcome: ok|error
)
GATEWAY_LATENCY = Histogram(
    'gateway_latency_seconds', 'Simulated payment gateway latency',
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 1.0, float("inf")]
)

# --- Risk/Fraud signals ---
FRAUD_SCORE = Histogram(
    'fraud_score', 'Simulated fraud score in [0..1]',
    buckets=[0.2, 0.4, 0.6, 0.8, 0.9, 1.0]
)

def simulate_gateway():
    """Simulate an external gateway call with latency and occasional errors."""
    t0 = time.perf_counter()
    time.sleep(random.uniform(0.05, 0.25))
    ok = random.random() > 0.05  # ~5% gateway errors
    GATEWAY_LATENCY.observe(time.perf_counter() - t0)
    GATEWAY_REQUESTS.labels(outcome=('ok' if ok else 'error')).inc()
    if not ok:
        raise RuntimeError("gateway_error")

@app.route('/transaction', methods=['POST'])
@TRANSACTION_LATENCY.time()
def transaction():
    TRANSACTION_IN_PROGRESS.inc()
    try:
        data = request.get_json() or {}
        amount = float(data.get('amount', 0))

        # Validation
        if amount <= 0:
            TRANSACTION_COUNT.labels(status='validation_error').inc()
            TRANSACTION_AMOUNT.labels(status='validation_error').observe(abs(amount))
            return jsonify({"status": "failed", "error": "invalid_amount"}), 400

        # Dependency call (e.g., payment gateway)
        try:
            simulate_gateway()
        except Exception:
            TRANSACTION_COUNT.labels(status='failed').inc()
            TRANSACTION_AMOUNT.labels(status='failed').observe(amount)
            return jsonify({"status": "failed", "error": "gateway"}), 502

        # App processing variability
        time.sleep(random.uniform(0.2, 1.0))

        # Risk assessment
        score = random.random()
        FRAUD_SCORE.observe(score)
        if score > 0.95:
            TRANSACTION_COUNT.labels(status='blocked_fraud').inc()
            TRANSACTION_AMOUNT.labels(status='blocked_fraud').observe(amount)
            return jsonify({"status": "failed", "error": "blocked_fraud", "fraud_score": score}), 403

        # Business outcome (~90% success)
        success = random.random() > 0.1
        if success:
            TRANSACTION_COUNT.labels(status='success').inc()
            TRANSACTION_AMOUNT.labels(status='success').observe(amount)
            return jsonify({"status": "success", "amount": amount, "fraud_score": score}), 200
        else:
            TRANSACTION_COUNT.labels(status='failed').inc()
            TRANSACTION_AMOUNT.labels(status='failed').observe(amount)
            return jsonify({"status": "failed", "error": "processing"}), 500

    finally:
        TRANSACTION_IN_PROGRESS.dec()

@app.route('/alert', methods=['POST'])
def alert():
    """Alertmanager webhook endpoint for demo; logs payload for Loki dashboards."""
    payload = request.get_json(silent=True) or {}
    app.logger.info(json.dumps({"event": "alert_received", "payload": payload}))
    return jsonify({"received": True}), 200

@app.route('/health')
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/')
def home():
    return "Financial Transaction Service — Observability Demo"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

