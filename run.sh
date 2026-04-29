#!/usr/bin/env bash
# Launch the Goldmane Policy Impact Analyzer dashboard.
# Prerequisites:
#   - Python 3.11+
#   - Dependencies installed: pip install -r requirements.txt
#   - For LIVE mode: port-forward running (scripts/port-forward.sh) + certs in certs/
#   - For DEMO mode: just run this script (no cluster needed)

set -euo pipefail
cd "$(dirname "$0")"

# Activate venv if present, otherwise fall back to system Python
if [[ -f venv/bin/activate ]]; then
  source venv/bin/activate
fi

# Generate Python gRPC stubs if not already done
if [[ ! -f grpc_libs/api_pb2.py ]]; then
  echo "==> Generating gRPC stubs..."
  python3 -m grpc_tools.protoc \
    --proto_path=grpc_libs \
    --python_out=grpc_libs \
    --grpc_python_out=grpc_libs \
    grpc_libs/api.proto
fi

# Load .env if present
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

# Default: demo mode unless GOLDMANE_HOST is set
if [[ -z "${GOLDMANE_HOST:-}" ]]; then
  echo "==> GOLDMANE_HOST not set — starting in DEMO mode (synthetic data)"
  echo "    To use a live cluster:"
  echo "      1. Run scripts/port-forward.sh in another terminal"
  echo "      2. export GOLDMANE_HOST=127.0.0.1"
  echo "      3. ./run.sh"
  echo ""
  export DEMO_MODE=true
fi

echo "==> Starting Goldmane Policy Impact Analyzer..."
echo "    Dashboard will open at http://localhost:8501"
echo ""

streamlit run analyzer/dashboard.py \
  --server.port "${STREAMLIT_PORT:-8501}" \
  --server.headless true \
  --browser.gatherUsageStats false
