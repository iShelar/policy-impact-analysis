# Goldmane Policy Impact Analyzer

**Calico 3.30+ Hackathon 2026 Submission**

A real-time dashboard that shows exactly what will happen to your cluster traffic **before** you promote a Staged Network Policy to enforcement. It uses **Goldmane** (Calico's high-speed flow-log gRPC API) to pull live traffic data and overlay it against **Staged Policies** — eliminating the fear of breaking production with new security rules.

---

## The Problem

Security teams hesitate to enforce new network policies because they can't predict the blast radius. "Will this policy break the payment service? Will it block Prometheus scraping? Will 1000 legitimate connections get dropped?"

Staged Policies let you test policies without enforcing them — but you still need a way to *read* their impact. That's what this tool does.

---

## How It Works

```
Live Cluster Traffic
       │
       ▼
  Goldmane gRPC API  ──►  Statistics service (per-staged-policy allow/deny counts)
       │                   Flows service (which policies match each flow)
       ▼
  Python Analyzer
       │
       ▼
  Streamlit Dashboard
  ├── Policy Impact Chart  (allowed vs denied packets per staged policy)
  ├── Live Flow Monitor    (real flows + which staged policies would match)
  ├── External Egress      (pods contacting public IPs — flags suspicious behaviour)
  └── Promotion Advisor    (risk score + "safe to promote?" recommendation)
```

---

## Key Features

| Feature | What it shows |
|---|---|
| **Policy Impact Chart** | Stacked bar: packets each staged policy would allow vs deny |
| **Time-series Denial Rate** | 15-second intervals showing how denial rate evolves over time |
| **Live Flow Monitor** | Filterable table of flows with `pending_policies` column |
| **External Egress Analysis** | Pods connecting to external IPs; flags those with > 5 unique destinations |
| **Promotion Advisor** | Risk score (LOW/MEDIUM/HIGH) + data-backed promote/review/reject recommendation |
| **Demo Mode** | Fully functional with synthetic data — no cluster required |

---

## Quick Start (Demo Mode — no cluster needed)

```bash
git clone <this-repo>
cd policy-impact-analysis

# Install dependencies
pip3 install -r requirements.txt

# Launch in demo mode (uses realistic synthetic data)
./run.sh
```

Open http://localhost:8501

---

## Full Setup (Live Cluster)

### Prerequisites

- Docker Desktop
- `kind` (`brew install kind`)
- `kubectl`
- Python 3.11+

### Step 1 — Create the cluster

```bash
bash scripts/01-create-cluster.sh
```

Creates a 3-node Kind cluster with CNI disabled (ready for Calico).

### Step 2 — Install Calico 3.31

```bash
bash scripts/02-install-calico.sh
```

Installs Calico via the Tigera Operator. The `custom-resources.yaml` automatically enables **Goldmane** and **Whisker**. Wait ~90 seconds for all pods to become Ready.

### Step 3 — Deploy the demo app + staged policies

```bash
bash scripts/03-deploy-app.sh
```

Deploys:
- `frontend` (nginx) + `backend` (Python HTTP) in `default` namespace
- `payment-api` in `payment` namespace  
- `prometheus` in `monitoring` namespace
- `traffic-gen` — a curl loop that generates realistic cross-service traffic

Then applies 5 staged policies with varying risk profiles:

| Policy | Risk | Why |
|---|---|---|
| `allow-frontend-to-backend` | 🟢 LOW | ~2% denial rate |
| `allow-monitoring-scrape` | 🟢 LOW | ~1% denial rate |
| `allow-internal-dns` | 🟢 LOW | ~0.6% denial rate |
| `deny-backend-to-internet` | 🔴 HIGH | ~33% of backend egress blocked |
| `isolate-payment-namespace` | 🔴 HIGH | ~54% of payment traffic blocked |

### Step 4 — Extract Goldmane certs

```bash
bash scripts/04-extract-certs.sh
```

Pulls the mTLS CA bundle and client cert/key from the cluster into `certs/`.

### Step 5 — Port-forward Goldmane (in a separate terminal)

```bash
bash scripts/port-forward.sh
```

Exposes Goldmane's gRPC endpoint at `localhost:7443`.

### Step 6 — Launch the dashboard

```bash
export GOLDMANE_HOST=127.0.0.1
./run.sh
```

Open http://localhost:8501. The status badge shows **● LIVE** when connected to Goldmane.

---

## Project Structure

```
.
├── analyzer/
│   ├── dashboard.py        # Streamlit UI — main entry point
│   ├── goldmane_client.py  # gRPC client (Statistics + Flows services)
│   ├── mock_data.py        # Synthetic demo data generator
│   ├── processor.py        # Data transformation + risk scoring
│   └── config.py           # Environment-based configuration
├── grpc_libs/
│   ├── api.proto           # Goldmane protobuf definition
│   ├── api_pb2.py          # Generated message stubs (auto-created by run.sh)
│   └── api_pb2_grpc.py     # Generated service stubs (auto-created by run.sh)
├── setup/
│   ├── kind-config.yaml    # 3-node Kind cluster spec
│   ├── demo-app.yaml       # Multi-service demo application
│   ├── staged-policies.yaml # 5 staged policies for testing
│   └── goldmane-svc.yaml   # Optional NodePort service for Goldmane
├── scripts/
│   ├── 01-create-cluster.sh
│   ├── 02-install-calico.sh
│   ├── 03-deploy-app.sh
│   ├── 04-extract-certs.sh
│   └── port-forward.sh
├── certs/                  # Extracted from cluster (gitignored)
├── requirements.txt
└── run.sh                  # One-command launcher
```

---

## Calico Features Used

### Goldmane (Flow Logs API)
- **`Statistics.List`** — per-staged-policy packet counts with 15-second time-series resolution
- **`Flows.List`** — individual flows with `pending_policies` (staged policy trace)
- **mTLS authentication** — gRPC over `ssl_channel_credentials` with cluster-issued certs
- **`PolicyKind.StagedNetworkPolicy`** filter — targets only staged (non-enforced) policies

### Staged Network Policies
- All 5 policies use `StagedNetworkPolicy` kind — Calico records flow impact without blocking traffic
- The `pending_policies` field in `FlowKey.policies` shows what would have matched
- Policies span multiple namespaces and tiers to demonstrate full cluster coverage

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `GOLDMANE_HOST` | `""` | Goldmane IP/hostname (triggers live mode when set) |
| `GOLDMANE_PORT` | `7443` | gRPC port |
| `GOLDMANE_CA_CERT` | `certs/goldmane-ca.crt` | CA bundle path |
| `GOLDMANE_CLIENT_CERT` | `certs/goldmane.crt` | Client cert path |
| `GOLDMANE_CLIENT_KEY` | `certs/goldmane.key` | Client key path |
| `DEMO_MODE` | `false` | Force demo mode with synthetic data |
| `LOOKBACK_SECONDS` | `-3600` | How far back to query flows |

---

## Hackathon Submission

**Category:** Observability + Zero Trust  
**Calico features:** Goldmane (flow logs), Staged Network Policies  
**Tag:** `calico-330-hackathon`
