"""
Generates realistic synthetic data for demo mode.
Used when Goldmane is unreachable or DEMO_MODE=true.
"""

import random
import time

STAGED_POLICIES = [
    {"name": "allow-frontend-to-backend", "namespace": "default", "tier": "default"},
    {"name": "deny-backend-to-internet", "namespace": "default", "tier": "default"},
    {"name": "allow-monitoring-scrape", "namespace": "monitoring", "tier": "default"},
    {"name": "isolate-payment-service", "namespace": "payment", "tier": "security"},
    {"name": "allow-internal-dns", "namespace": "kube-system", "tier": "default"},
]

PODS = [
    ("frontend", "default"),
    ("backend", "default"),
    ("payment-api", "payment"),
    ("postgres", "database"),
    ("prometheus", "monitoring"),
    ("nginx-ingress", "ingress"),
]

EXTERNAL_IPS = [
    "8.8.8.8", "1.1.1.1", "142.250.80.14",  # Google/Cloudflare (normal)
    "185.220.101.47", "103.21.244.0", "198.54.117.197",  # suspicious
    "51.89.64.50", "95.216.228.109",
]


def _make_time_series(n_points: int, base_allowed: int, base_denied: int, variance: float = 0.2):
    now = int(time.time())
    timestamps = [now - (n_points - i) * 15 for i in range(n_points)]
    allowed = [max(0, int(base_allowed * (1 + random.uniform(-variance, variance)))) for _ in range(n_points)]
    denied = [max(0, int(base_denied * (1 + random.uniform(-variance, variance)))) for _ in range(n_points)]
    return timestamps, allowed, denied


def get_staged_policy_stats() -> list[dict]:
    profiles = [
        (320, 8),    # allow-frontend-to-backend: mostly allowed
        (90, 45),    # deny-backend-to-internet: ~33% denied
        (210, 3),    # allow-monitoring-scrape: very safe
        (55, 62),    # isolate-payment-service: HIGH risk - more denied than allowed
        (180, 2),    # allow-internal-dns: safe
    ]
    results = []
    for policy, (base_allow, base_deny) in zip(STAGED_POLICIES, profiles):
        n = 24  # 24 data points (6 minutes of 15-second intervals)
        ts, allowed_in, denied_in = _make_time_series(n, base_allow, base_deny)
        _, allowed_out, denied_out = _make_time_series(n, int(base_allow * 0.85), int(base_deny * 0.9))
        results.append({
            "name": policy["name"],
            "namespace": policy["namespace"],
            "tier": policy["tier"],
            "kind": "StagedNetworkPolicy",
            "allowed_in": allowed_in,
            "denied_in": denied_in,
            "allowed_out": allowed_out,
            "denied_out": denied_out,
            "timestamps": ts,
        })
    return results


def get_recent_flows(n: int = 150) -> list[dict]:
    now = int(time.time())
    flows = []
    for _ in range(n):
        src_pod, src_ns = random.choice(PODS)
        dst_pod, dst_ns = random.choice(PODS)
        if src_pod == dst_pod:
            dst_pod, dst_ns = random.choice(PODS)
        is_external = random.random() < 0.12
        if is_external:
            dst_name = random.choice(EXTERNAL_IPS)
            dst_ns = ""
            dst_type = "Network"
            port = random.choice([80, 443, 8080, 9090])
        else:
            dst_name = dst_pod
            dst_type = "WorkloadEndpoint"
            port = random.choice([80, 443, 8080, 9090, 5432, 6379])

        action = "Allow" if random.random() > 0.08 else "Deny"
        staged_hits = []
        if random.random() > 0.4:
            p = random.choice(STAGED_POLICIES)
            staged_action = "Allow" if random.random() > 0.25 else "Deny"
            staged_hits.append({
                "name": p["name"],
                "namespace": p["namespace"],
                "action": staged_action,
                "kind": "StagedNetworkPolicy",
            })

        flows.append({
            "start_time": now - random.randint(0, 3600),
            "source_name": f"{src_pod}-{random.randint(10000,99999):x}",
            "source_namespace": src_ns,
            "source_type": "WorkloadEndpoint",
            "dest_name": dst_name if is_external else f"{dst_name}-{random.randint(10000,99999):x}",
            "dest_namespace": dst_ns,
            "dest_type": dst_type,
            "dest_port": port,
            "proto": random.choice(["TCP", "TCP", "TCP", "UDP"]),
            "action": action,
            "packets_in": random.randint(1, 500),
            "packets_out": random.randint(1, 300),
            "bytes_in": random.randint(100, 50000),
            "pending_staged_policies": staged_hits,
            "num_connections": random.randint(1, 20),
        })
    flows.sort(key=lambda x: x["start_time"], reverse=True)
    return flows
