#!/usr/bin/env python3
import argparse, json, time, random, os
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean
import requests

def rand_amount(max_amt: int = 1000) -> float:
    return float(random.randint(1, max_amt))

def percentile(values, p):
    if not values:
        return 0.0
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * p
    f = int(k)
    c = min(f + 1, len(values_sorted) - 1)
    if f == c:
        return values_sorted[int(k)]
    d0 = values_sorted[f] * (c - k)
    d1 = values_sorted[c] * (k - f)
    return d0 + d1

def one_call(base_url: str, timeout: float = 5.0):
    amt = rand_amount()
    url = f"{base_url.rstrip('/')}/transaction"
    t0 = time.perf_counter()
    try:
        resp = requests.post(url, json={"amount": amt}, timeout=timeout)
        latency = (time.perf_counter() - t0) * 1000.0
        ok = resp.status_code == 200
        return {"ok": ok, "status": resp.status_code, "latency_ms": latency, "amount": amt}
    except Exception as e:
        latency = (time.perf_counter() - t0) * 1000.0
        return {"ok": False, "status": "EXC", "latency_ms": latency, "amount": amt, "error": str(e)}

def run_load(base_url: str, rps: float, duration_s: int, workers: int):
    interval = 1.0 / max(rps, 0.001)
    deadline = time.time() + duration_s
    samples = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = []
        next_at = time.perf_counter()
        while time.time() < deadline:
            futures.append(pool.submit(one_call, base_url))
            next_at += interval
            now = time.perf_counter()
            sleep_for = next_at - now
            if sleep_for > 0:
                time.sleep(sleep_for)
        for fut in as_completed(futures):
            samples.append(fut.result())
    return samples

def summarize(samples):
    latencies = [s["latency_ms"] for s in samples]
    oks = [s for s in samples if s["ok"]]
    fails = [s for s in samples if not s["ok"]]
    total = len(samples)
    succ = len(oks)
    fail = len(fails)
    err_rate = (fail / total) if total else 0.0
    summary = {
        "total": total,
        "success": succ,
        "failed": fail,
        "error_rate": err_rate,
        "latency_ms": {
            "avg": mean(latencies) if latencies else 0.0,
            "p50": percentile(latencies, 0.50),
            "p90": percentile(latencies, 0.90),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
        }
    }
    return summary

def save_outputs(samples, summary, outdir: str):
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "load_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(outdir, "load_samples.csv"), "w", encoding="utf-8") as f:
        f.write("ok,status,latency_ms,amount\n")
        for s in samples:
            f.write(f"{int(s['ok'])},{s['status']},{s['latency_ms']:.2f},{s['amount']}\n")

def main():
    parser = argparse.ArgumentParser(description="Simple load test for fintech Flask service")
    parser.add_argument("--base-url", default="http://localhost:5000", help="Base URL of the service")
    parser.add_argument("--rps", type=float, default=12.0, help="Target requests per second")
    parser.add_argument("--duration", type=int, default=180, help="Duration in seconds")
    parser.add_argument("--workers", type=int, default=30, help="Max concurrent workers")
    parser.add_argument("--outdir", default="load_output", help="Output directory")
    args = parser.parse_args()

    print(f"[load] Target: {args.base_url} | rps={args.rps} | duration={args.duration}s | workers={args.workers}")
    samples = run_load(args.base_url, args.rps, args.duration, args.workers)
    summary = summarize(samples)
    save_outputs(samples, summary, args.outdir)
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
