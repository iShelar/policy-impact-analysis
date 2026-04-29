#!/usr/bin/env bash
# Expose Goldmane gRPC locally via port-forward.
# Run this in a SEPARATE terminal before launching the dashboard.
set -euo pipefail

echo "==> Starting port-forward: localhost:7443 → goldmane:7443"
echo "    Keep this terminal open while using the dashboard."
echo "    Then in another terminal: export GOLDMANE_HOST=127.0.0.1 && ./run.sh"
echo ""

echo "Whisker UI also available — run in a separate terminal:"
echo "  kubectl port-forward -n calico-system svc/whisker 8081:8081"
echo ""

kubectl port-forward \
  -n calico-system \
  svc/goldmane \
  7443:7443
