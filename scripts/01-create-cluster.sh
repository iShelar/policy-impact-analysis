#!/usr/bin/env bash
# Step 1: Create a 3-node Kind cluster with Calico as CNI
set -euo pipefail

CLUSTER_NAME="calico-cluster"

echo "==> Checking for existing cluster..."
if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
  echo "    Cluster '${CLUSTER_NAME}' already exists. Delete it first with:"
  echo "    kind delete cluster --name ${CLUSTER_NAME}"
  exit 0
fi

echo "==> Creating Kind cluster..."
kind create cluster \
  --name "${CLUSTER_NAME}" \
  --config setup/kind-config.yaml \
  --wait 90s

echo "==> Verifying nodes (expect 3: 1 control-plane + 2 workers)..."
kubectl get nodes

echo ""
echo "✅ Cluster created. Next: run scripts/02-install-calico.sh"
