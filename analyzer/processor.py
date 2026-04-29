"""
Processes raw flow and statistics data into display-ready structures.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import datetime


EXTERNAL_THRESHOLD = 5  # pods with more unique external IPs are flagged suspicious


def process_policy_stats(raw_stats: list[dict]) -> pd.DataFrame:
    """
    Convert raw stats list into a summary DataFrame per staged policy.
    Columns: name, namespace, total_allowed, total_denied, denial_rate, risk_level, recommendation
    """
    rows = []
    for s in raw_stats:
        total_allowed = sum(s.get("allowed_in", [])) + sum(s.get("allowed_out", []))
        total_denied = sum(s.get("denied_in", [])) + sum(s.get("denied_out", []))
        total = total_allowed + total_denied
        denial_rate = (total_denied / total * 100) if total > 0 else 0.0

        risk_level, recommendation = _risk_assessment(denial_rate, total)

        rows.append({
            "Policy": s["name"],
            "Namespace": s["namespace"],
            "Tier": s.get("tier", "default"),
            "Allowed Pkts": total_allowed,
            "Denied Pkts": total_denied,
            "Denial Rate %": round(denial_rate, 1),
            "Risk": risk_level,
            "Recommendation": recommendation,
        })

    if not rows:
        return pd.DataFrame(columns=["Policy", "Namespace", "Tier", "Allowed Pkts",
                                     "Denied Pkts", "Denial Rate %", "Risk", "Recommendation"])
    return pd.DataFrame(rows).sort_values("Denial Rate %", ascending=False)


def _risk_assessment(denial_rate: float, total_flows: int) -> tuple[str, str]:
    if denial_rate == 0 and total_flows == 0:
        return "UNKNOWN", "No traffic matched this policy yet"
    if denial_rate < 5:
        return "LOW", "Safe to promote — minimal traffic would be denied"
    if denial_rate < 25:
        return "MEDIUM", "Review denied flows before promoting"
    return "HIGH", "Do NOT promote — significant traffic would be blocked"


def flows_to_dataframe(flows: list[dict]) -> pd.DataFrame:
    if not flows:
        return pd.DataFrame()
    rows = []
    for f in flows:
        staged_hits = f.get("pending_staged_policies", [])
        staged_str = ", ".join(
            f"{p['name']} ({p['action']})" for p in staged_hits
        ) if staged_hits else "—"
        rows.append({
            "Time": datetime.fromtimestamp(f["start_time"]).strftime("%H:%M:%S"),
            "Source": f"{f['source_name']}/{f['source_namespace']}",
            "Destination": f"{f['dest_name']}:{f['dest_port']}",
            "Proto": f["proto"],
            "Action": f["action"],
            "Packets": f["packets_in"],
            "Staged Policy Hits": staged_str,
        })
    return pd.DataFrame(rows)


def get_external_connections(flows: list[dict]) -> pd.DataFrame:
    """
    Find pods making connections to external (non-cluster) IPs.
    Groups by source pod, counts unique external destinations.
    """
    ext_flows = [f for f in flows if f.get("dest_type") in ("Network", "")]
    if not ext_flows:
        return pd.DataFrame(columns=["Pod", "Namespace", "External IPs", "Count", "Status"])

    from collections import defaultdict
    pod_ips: dict[tuple, set] = defaultdict(set)
    for f in ext_flows:
        key = (f["source_name"], f["source_namespace"])
        pod_ips[key].add(f["dest_name"])

    rows = []
    for (pod, ns), ips in sorted(pod_ips.items(), key=lambda x: -len(x[1])):
        count = len(ips)
        status = "SUSPICIOUS" if count >= EXTERNAL_THRESHOLD else "Normal"
        rows.append({
            "Pod": pod,
            "Namespace": ns,
            "External IPs": ", ".join(sorted(ips)[:5]) + ("..." if count > 5 else ""),
            "Count": count,
            "Status": status,
        })
    return pd.DataFrame(rows)


def build_timeseries_df(raw_stats: list[dict]) -> pd.DataFrame:
    """
    Build a long-format DataFrame for time-series charts.
    Columns: timestamp, policy, allowed, denied
    """
    rows = []
    for s in raw_stats:
        ts = s.get("timestamps", [])
        allowed = s.get("allowed_in", [])
        denied = s.get("denied_in", [])
        for i, t in enumerate(ts):
            rows.append({
                "timestamp": datetime.fromtimestamp(t),
                "policy": s["name"],
                "allowed": allowed[i] if i < len(allowed) else 0,
                "denied": denied[i] if i < len(denied) else 0,
            })
    if not rows:
        return pd.DataFrame(columns=["timestamp", "policy", "allowed", "denied"])
    return pd.DataFrame(rows)
