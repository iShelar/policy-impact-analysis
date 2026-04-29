#!/usr/bin/env bash
# Step 2: Install Calico 3.31 via the Tigera Operator + enable Goldmane & Whisker
set -euo pipefail

CALICO_VERSION="v3.31.4"

echo "==> Installing Tigera Operator CRDs..."
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/${CALICO_VERSION}/manifests/operator-crds.yaml" \
  --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || \
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/${CALICO_VERSION}/manifests/operator-crds.yaml" || true

echo "==> Installing Tigera Operator..."
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/${CALICO_VERSION}/manifests/tigera-operator.yaml" || true

echo "==> Applying Calico custom resources (enables Goldmane + Whisker automatically)..."
kubectl create -f "https://raw.githubusercontent.com/projectcalico/calico/${CALICO_VERSION}/manifests/custom-resources.yaml" || true

echo "==> Waiting for calico-system pods to be Ready (this takes ~90 seconds)..."
kubectl wait --for=condition=Ready pods \
  --all -n calico-system \
  --timeout=180s 2>/dev/null || true

echo "==> Checking Calico component status..."
kubectl get pods -n calico-system

echo ""
echo "==> Verifying Goldmane is running..."
kubectl get pods -n calico-system -l app=goldmane 2>/dev/null || echo "  (Goldmane pod not yet listed — may still be starting)"

echo ""
echo "==> Node status:"
kubectl get nodes

echo ""
echo "✅ Calico installed. Next: run scripts/03-deploy-app.sh"
