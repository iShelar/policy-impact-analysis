#!/usr/bin/env bash
# Step 4: Extract Goldmane mTLS certs from the cluster
# These are needed for the Python gRPC client to authenticate with Goldmane.
set -euo pipefail

CERT_DIR="certs"
mkdir -p "${CERT_DIR}"

echo "==> Extracting Goldmane CA certificate..."
kubectl get configmap goldmane-ca-bundle \
  -n calico-system \
  -o jsonpath="{.data.tigera-ca-bundle\.crt}" \
  > "${CERT_DIR}/goldmane-ca.crt"
echo "    Saved: ${CERT_DIR}/goldmane-ca.crt"

echo "==> Extracting Goldmane client certificate..."
kubectl get secret goldmane-key-pair \
  -n calico-system \
  -o jsonpath="{.data.tls\.crt}" \
  | base64 -d \
  > "${CERT_DIR}/goldmane.crt"
echo "    Saved: ${CERT_DIR}/goldmane.crt"

echo "==> Extracting Goldmane client private key..."
kubectl get secret goldmane-key-pair \
  -n calico-system \
  -o jsonpath="{.data.tls\.key}" \
  | base64 -d \
  > "${CERT_DIR}/goldmane.key"
chmod 600 "${CERT_DIR}/goldmane.key"
echo "    Saved: ${CERT_DIR}/goldmane.key"

echo ""
echo "==> Verifying cert files:"
for f in "${CERT_DIR}/goldmane-ca.crt" "${CERT_DIR}/goldmane.crt" "${CERT_DIR}/goldmane.key"; do
  if [[ -s "$f" ]]; then
    echo "    ✅ $f ($(wc -c < "$f") bytes)"
  else
    echo "    ❌ $f — empty or missing!"
  fi
done

echo ""
echo "==> Getting Goldmane endpoint..."
echo "    Run the port-forward in a separate terminal (scripts/port-forward.sh)"
echo "    Then set: export GOLDMANE_HOST=127.0.0.1"
echo ""
echo "✅ Certs extracted. Next: run scripts/port-forward.sh in another terminal, then run.sh"
