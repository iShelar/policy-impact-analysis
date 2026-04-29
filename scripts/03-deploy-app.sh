#!/usr/bin/env bash
# Step 3: Deploy the demo application and staged policies
set -euo pipefail

echo "==> Deploying demo multi-service application..."
kubectl apply -f setup/demo-app.yaml

echo "==> Waiting for demo pods to be Ready..."
kubectl wait --for=condition=Ready pods \
  -l 'app in (frontend,backend,traffic-gen)' \
  -n default --timeout=120s 2>/dev/null || true

kubectl wait --for=condition=Ready pods \
  -l app=payment-api \
  -n payment --timeout=120s 2>/dev/null || true

kubectl wait --for=condition=Ready pods \
  -l app=prometheus \
  -n monitoring --timeout=120s 2>/dev/null || true

echo ""
echo "==> Pod status:"
kubectl get pods -A -l 'app in (frontend,backend,traffic-gen,payment-api,prometheus)'

echo ""
echo "==> Applying staged network policies..."
kubectl apply -f setup/staged-policies.yaml

echo ""
echo "==> Staged policies applied:"
kubectl get stagednetworkpolicies -A 2>/dev/null || echo "  (StagedNetworkPolicy CRD not found — ensure Calico is installed)"

echo ""
echo "✅ Demo app and staged policies deployed."
echo "   Traffic generator is running. Wait ~2 minutes for flows to accumulate."
echo "   Next: run scripts/04-extract-certs.sh"
