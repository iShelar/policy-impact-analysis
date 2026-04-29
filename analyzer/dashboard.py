"""
Goldmane Policy Impact Analyzer – Streamlit Dashboard
"""

import os
import sys
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analyzer.config import Config
from analyzer.processor import (
    process_policy_stats,
    flows_to_dataframe,
    get_external_connections,
    build_timeseries_df,
)
import analyzer.mock_data as mock_data

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Goldmane Policy Impact Analyzer",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 2rem; font-weight: 700; }
    .risk-high  { color: #ef4444; font-weight: 700; }
    .risk-med   { color: #f59e0b; font-weight: 700; }
    .risk-low   { color: #10b981; font-weight: 700; }
    .risk-unk   { color: #6b7280; }
    .badge-live { background:#10b981; color:white; border-radius:12px;
                  padding:2px 10px; font-size:0.75rem; font-weight:700; }
    .badge-demo { background:#f59e0b; color:white; border-radius:12px;
                  padding:2px 10px; font-size:0.75rem; font-weight:700; }
    .badge-err  { background:#ef4444; color:white; border-radius:12px;
                  padding:2px 10px; font-size:0.75rem; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://www.tigera.io/app/uploads/2022/06/Calico-logo-black-1-1.svg",
             use_container_width=True)
    st.title("Policy Analyzer")
    st.divider()

    st.subheader("Goldmane Connection")
    host = st.text_input("Host", value=os.getenv("GOLDMANE_HOST", ""))
    port = st.number_input("Port", value=7443, min_value=1, max_value=65535)
    ca_cert = st.text_input("CA Cert", value="certs/goldmane-ca.crt")
    client_cert = st.text_input("Client Cert", value="certs/goldmane.crt")
    client_key = st.text_input("Client Key", value="certs/goldmane.key")

    st.divider()
    st.subheader("Settings")
    lookback = st.selectbox(
        "Time Range",
        options=[("-900", "Last 15 min"), ("-3600", "Last 1 hour"),
                 ("-21600", "Last 6 hours"), ("-86400", "Last 24 hours")],
        index=1,
        format_func=lambda x: x[1],
    )
    refresh_interval = st.selectbox(
        "Auto-refresh",
        options=[(15, "Every 15s"), (30, "Every 30s"), (60, "Every 60s"), (0, "Off")],
        format_func=lambda x: x[1],
    )
    demo_override = st.checkbox("Force Demo Mode", value=False)

    st.divider()
    st.caption("Calico Hackathon 2026 · Goldmane + Staged Policies")


# ── Auto-refresh ──────────────────────────────────────────────────────────────
if refresh_interval[0] > 0:
    st_autorefresh(interval=refresh_interval[0] * 1000, key="autorefresh")

# ── Data loading ──────────────────────────────────────────────────────────────
cfg = Config(
    goldmane_host=host,
    goldmane_port=int(port),
    ca_cert=ca_cert,
    client_cert=client_cert,
    client_key=client_key,
    demo_mode=demo_override,
    lookback_seconds=int(lookback[0]),
)

connection_status = "demo"
raw_stats: list[dict] = []
raw_flows: list[dict] = []
error_msg = ""

if not demo_override and host and cfg.certs_exist():
    try:
        from analyzer.goldmane_client import GoldmaneClient
        client = GoldmaneClient(cfg)
        if client.health_check(timeout=3.0):
            raw_stats = client.get_staged_policy_stats()
            raw_flows = client.list_recent_flows(page_size=300)
            client.close()
            connection_status = "live"
        else:
            error_msg = f"Goldmane at {host}:{port} is not responding."
            connection_status = "error"
            raw_stats = mock_data.get_staged_policy_stats()
            raw_flows = mock_data.get_recent_flows()
    except Exception as e:
        error_msg = str(e)
        connection_status = "error"
        raw_stats = mock_data.get_staged_policy_stats()
        raw_flows = mock_data.get_recent_flows()
else:
    raw_stats = mock_data.get_staged_policy_stats()
    raw_flows = mock_data.get_recent_flows()

policy_df = process_policy_stats(raw_stats)
flows_df = flows_to_dataframe(raw_flows)
external_df = get_external_connections(raw_flows)
timeseries_df = build_timeseries_df(raw_stats)

# ── Header ────────────────────────────────────────────────────────────────────
col_title, col_status = st.columns([6, 1])
with col_title:
    st.title("🛡️ Goldmane Policy Impact Analyzer")
    st.caption("Preview the real-world impact of Staged Network Policies using Goldmane flow data")
with col_status:
    st.write("")
    st.write("")
    if connection_status == "live":
        st.markdown('<span class="badge-live">● LIVE</span>', unsafe_allow_html=True)
        st.caption(f"{host}:{port}")
    elif connection_status == "error":
        st.markdown('<span class="badge-err">● ERROR</span>', unsafe_allow_html=True)
        st.caption(error_msg[:60])
    else:
        st.markdown('<span class="badge-demo">● DEMO</span>', unsafe_allow_html=True)
        st.caption("Using synthetic data")

if connection_status == "error":
    st.warning(f"⚠️ Could not connect to Goldmane: {error_msg} — showing demo data.")

# ── Summary metrics ───────────────────────────────────────────────────────────
st.divider()
total_flows = len(raw_flows)
staged_count = len(policy_df)
total_allowed = int(policy_df["Allowed Pkts"].sum()) if not policy_df.empty else 0
total_denied = int(policy_df["Denied Pkts"].sum()) if not policy_df.empty else 0
total_pkts = total_allowed + total_denied
overall_denial = round(total_denied / total_pkts * 100, 1) if total_pkts > 0 else 0.0
high_risk = len(policy_df[policy_df["Risk"] == "HIGH"]) if not policy_df.empty else 0
suspicious_pods = len(external_df[external_df["Status"] == "SUSPICIOUS"]) if not external_df.empty else 0

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Staged Policies", staged_count)
m2.metric("Flows Analyzed", f"{total_flows:,}")
m3.metric("Would Be Denied", f"{overall_denial}%",
          delta=f"{total_denied:,} pkts", delta_color="inverse")
m4.metric("High Risk Policies", high_risk,
          delta="Need review" if high_risk > 0 else "All clear",
          delta_color="inverse" if high_risk > 0 else "normal")
m5.metric("Suspicious Pods", suspicious_pods,
          delta="External egress" if suspicious_pods > 0 else "Normal",
          delta_color="inverse" if suspicious_pods > 0 else "normal")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Policy Impact", "🔄 Flow Monitor", "🌐 External Egress", "🎯 Promotion Advisor"
])

# ── Tab 1: Policy Impact ──────────────────────────────────────────────────────
with tab1:
    st.subheader("Staged Policy Impact – Packet Analysis")
    st.caption("Shows how many packets each staged policy would Allow vs Deny if promoted to enforced.")

    if policy_df.empty:
        st.info("No staged policies found. Apply some StagedNetworkPolicies to see impact data.")
    else:
        col_chart, col_table = st.columns([3, 2])
        with col_chart:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Would Allow",
                x=policy_df["Policy"],
                y=policy_df["Allowed Pkts"],
                marker_color="#10b981",
                hovertemplate="<b>%{x}</b><br>Allowed: %{y:,}<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                name="Would Deny",
                x=policy_df["Policy"],
                y=policy_df["Denied Pkts"],
                marker_color="#ef4444",
                hovertemplate="<b>%{x}</b><br>Denied: %{y:,}<extra></extra>",
            ))
            fig.update_layout(
                barmode="group",
                title="Packet Impact per Staged Policy",
                xaxis_title="Staged Policy",
                yaxis_title="Packet Count",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                height=380,
                xaxis=dict(tickangle=-25),
            )
            st.plotly_chart(fig, use_container_width=True, key="policy_impact_bar")

        with col_table:
            def risk_badge(r):
                if r == "HIGH":
                    return "🔴 HIGH"
                if r == "MEDIUM":
                    return "🟡 MEDIUM"
                if r == "LOW":
                    return "🟢 LOW"
                return "⚪ UNKNOWN"

            display_df = policy_df.copy()
            display_df["Risk"] = display_df["Risk"].apply(risk_badge)
            st.dataframe(
                display_df[["Policy", "Namespace", "Denial Rate %", "Risk"]],
                use_container_width=True,
                hide_index=True,
                height=380,
            )

        st.divider()
        st.subheader("Denial Rate Over Time")
        if not timeseries_df.empty:
            denial_ts = timeseries_df.copy()
            denial_ts["denial_rate"] = (
                denial_ts["denied"] / (denial_ts["allowed"] + denial_ts["denied"] + 1) * 100
            )
            fig2 = px.line(
                denial_ts,
                x="timestamp",
                y="denial_rate",
                color="policy",
                title="Staged Policy Denial Rate (%) — 15-second intervals",
                labels={"denial_rate": "Denial Rate %", "timestamp": "Time", "policy": "Policy"},
                height=320,
            )
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(range=[0, 100]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig2, use_container_width=True, key="denial_timeseries")
        else:
            st.info("No time-series data available yet.")

# ── Tab 2: Flow Monitor ───────────────────────────────────────────────────────
with tab2:
    st.subheader("Live Flow Monitor")
    st.caption(
        "Recent flows with staged policy evaluation. "
        "'Staged Policy Hits' shows what policy would match if promoted."
    )

    if flows_df.empty:
        st.info("No flow data available.")
    else:
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        with col_filter1:
            action_filter = st.multiselect(
                "Filter by Action", ["Allow", "Deny"], default=["Allow", "Deny"]
            )
        with col_filter2:
            src_ns_opts = sorted(set(f["source_namespace"] for f in raw_flows))
            src_ns_filter = st.multiselect("Source Namespace", src_ns_opts, default=src_ns_opts)
        with col_filter3:
            has_staged = st.checkbox("Only flows with staged policy hits", value=False)

        filtered = flows_df.copy()
        if action_filter:
            filtered = filtered[filtered["Action"].isin(action_filter)]
        if src_ns_filter:
            filtered = filtered[
                filtered["Source"].apply(lambda s: s.split("/")[-1] in src_ns_filter)
            ]
        if has_staged:
            filtered = filtered[filtered["Staged Policy Hits"] != "—"]

        def color_action(val):
            if val == "Allow":
                return "color: #10b981; font-weight:600"
            if val == "Deny":
                return "color: #ef4444; font-weight:600"
            return ""

        def color_staged(val):
            if "Deny" in str(val):
                return "background-color: rgba(239,68,68,0.15)"
            if "Allow" in str(val):
                return "background-color: rgba(16,185,129,0.1)"
            return ""

        if filtered.empty or "Action" not in filtered.columns:
            st.info("No flows match the current filters.")
        else:
            styled = filtered.style.map(color_action, subset=["Action"])
            styled = styled.map(color_staged, subset=["Staged Policy Hits"])
            st.dataframe(styled, use_container_width=True, hide_index=True, height=500)
        st.caption(f"Showing {len(filtered):,} of {len(flows_df):,} flows")

        staged_only = [f for f in raw_flows if f.get("pending_staged_policies")]
        would_deny = [
            f for f in staged_only
            if any(p["action"] == "Deny" for p in f["pending_staged_policies"])
        ]
        if would_deny:
            st.warning(
                f"⚠️ {len(would_deny)} flows would be **denied** by staged policies if promoted."
            )

# ── Tab 3: External Egress ────────────────────────────────────────────────────
with tab3:
    st.subheader("External Egress Analysis")
    st.caption(
        "Pods contacting IPs outside the cluster. "
        "Pods with ≥ 5 unique external IPs are flagged **SUSPICIOUS**."
    )

    if external_df.empty:
        st.success("✅ No external connections detected in the selected time range.")
    else:
        suspicious_df = external_df[external_df["Status"] == "SUSPICIOUS"]
        normal_df = external_df[external_df["Status"] == "Normal"]

        if not suspicious_df.empty:
            st.error(f"🚨 {len(suspicious_df)} pod(s) with suspicious external egress detected!")
            st.dataframe(
                suspicious_df.style.map(
                    lambda v: "color: #ef4444; font-weight:700" if v == "SUSPICIOUS" else "",
                    subset=["Status"],
                ),
                use_container_width=True,
                hide_index=True,
            )
            st.caption("These pods may indicate data exfiltration or misconfigured workloads.")
            st.divider()

        if not normal_df.empty:
            st.subheader("Normal External Connections")
            st.dataframe(normal_df, use_container_width=True, hide_index=True)

        fig3 = px.bar(
            external_df.head(15),
            x="Pod",
            y="Count",
            color="Status",
            color_discrete_map={"SUSPICIOUS": "#ef4444", "Normal": "#10b981"},
            title="External IP Connections per Pod",
            labels={"Count": "Unique External IPs"},
            height=320,
        )
        fig3.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickangle=-25),
        )
        st.plotly_chart(fig3, use_container_width=True, key="external_bar")

# ── Tab 4: Promotion Advisor ──────────────────────────────────────────────────
with tab4:
    st.subheader("Policy Promotion Advisor")
    st.caption(
        "Data-driven recommendations on whether each staged policy is safe to promote "
        "to enforced mode, based on real cluster traffic."
    )

    if policy_df.empty:
        st.info("No staged policies found.")
    else:
        for _, row in policy_df.iterrows():
            risk = row["Risk"]
            if risk == "HIGH":
                icon, color, border = "🔴", "#ef4444", "#7f1d1d"
            elif risk == "MEDIUM":
                icon, color, border = "🟡", "#f59e0b", "#78350f"
            else:
                icon, color, border = "🟢", "#10b981", "#064e3b"

            with st.container():
                st.markdown(
                    f"""
                    <div style="border:1px solid {border}; border-radius:8px;
                                padding:16px; margin:8px 0; background:rgba(0,0,0,0.2)">
                        <h4 style="margin:0; color:{color}">{icon} {row['Policy']}</h4>
                        <p style="margin:4px 0; color:#9ca3af; font-size:0.85rem">
                            Namespace: <b>{row['Namespace']}</b> · Tier: <b>{row['Tier']}</b>
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                c1, c2, c3 = st.columns(3)
                c1.metric("Would Allow", f"{row['Allowed Pkts']:,} pkts")
                c2.metric("Would Deny", f"{row['Denied Pkts']:,} pkts")
                c3.metric("Denial Rate", f"{row['Denial Rate %']}%")

                denial_pct = row["Denial Rate %"]
                bar_val = min(denial_pct / 100, 1.0)
                fig_gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=denial_pct,
                    number={"suffix": "%"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": color},
                        "steps": [
                            {"range": [0, 5], "color": "rgba(16,185,129,0.15)"},
                            {"range": [5, 25], "color": "rgba(245,158,11,0.15)"},
                            {"range": [25, 100], "color": "rgba(239,68,68,0.15)"},
                        ],
                        "threshold": {"line": {"color": "white", "width": 2}, "value": denial_pct},
                    },
                    title={"text": "Denial Rate"},
                ))
                fig_gauge.update_layout(height=180, margin=dict(t=30, b=10, l=10, r=10),
                                         paper_bgcolor="rgba(0,0,0,0)")
                safe_key = row["Policy"].replace("-", "_").replace(" ", "_")
                st.plotly_chart(fig_gauge, use_container_width=True, key=f"gauge_{safe_key}")

                if risk == "HIGH":
                    st.error(f"❌ **Do NOT promote** — {denial_pct}% of traffic would be blocked. "
                             f"Review denied flows in the Flow Monitor tab first.")
                elif risk == "MEDIUM":
                    st.warning(f"⚠️ **Review before promoting** — {denial_pct}% denial rate. "
                               f"Inspect which pods are affected and confirm denials are intentional.")
                else:
                    st.success(f"✅ **Safe to promote** — Only {denial_pct}% of traffic would be "
                               f"denied. {row['Recommendation']}")
                st.divider()

    st.subheader("How to Promote a Policy")
    st.code(
        "# Convert a StagedNetworkPolicy to an enforced CalicoNetworkPolicy:\n"
        "kubectl get stagednetworkpolicy <name> -n <namespace> -o yaml \\\n"
        "  | sed 's/kind: StagedNetworkPolicy/kind: NetworkPolicy/' \\\n"
        "  | sed 's/apiVersion: projectcalico.org\\/v3/apiVersion: networking.k8s.io\\/v1/' \\\n"
        "  | kubectl apply -f -\n\n"
        "# Or use calicoctl:\n"
        "calicoctl patch stagednetworkpolicy <name> --patch '{\"spec\":{\"enforced\": true}}'",
        language="bash",
    )
