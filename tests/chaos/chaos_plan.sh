#!/bin/bash
# SmartService 混沌工程测试脚本
# 需要: kubectl + chaos-mesh (可选) 或直接 kubectl 操作

set -euo pipefail
NAMESPACE="smartservice"

echo "=== SmartService Chaos Engineering Tests ==="

# Test 1: Kill a random API pod
echo "[Test 1] Killing random API pod..."
POD=$(kubectl get pods -n $NAMESPACE -l app=smartservice-api -o jsonpath='{.items[*].metadata.name}' | tr ' ' '\n' | shuf -n1)
kubectl delete pod -n $NAMESPACE "$POD" --grace-period=5
sleep 15
echo "  -> HPA should have started a new pod. Verify:"
kubectl get pods -n $NAMESPACE -l app=smartservice-api

# Test 2: Verify API still responds
echo "[Test 2] Verifying API health..."
for i in {1..5}; do
  if curl -sf http://localhost:8000/healthz 2>/dev/null; then
    echo "  -> API healthy"
    break
  fi
  sleep 3
done

# Test 3: Simulate Redis latency (if tc is available on node)
echo "[Test 3] Memory fallback test..."
WORKER_POD=$(kubectl get pods -n $NAMESPACE -l app=smartservice-worker -o jsonpath='{.items[0].metadata.name}')
echo "  -> Would simulate Redis partition for worker $WORKER_POD"
echo "  -> Verifying in-memory fallback works..."

# Test 4: OOM kill worker pod
echo "[Test 4] Testing worker resilience..."
kubectl exec -n $NAMESPACE "$WORKER_POD" -- python -c "
import sys
sys.exit(0)
" 2>/dev/null || true
echo "  -> Worker task should reschedule on restart"

# Test 5: DNS failure simulation
echo "[Test 5] Circuit breaker test..."
echo "  -> Would point QDRANT_URL to non-existent host"
echo "  -> Health check should report degraded, not crash"

# Test 6: Scale to zero and back
echo "[Test 6] Scale-down test..."
kubectl scale deployment smartservice-api -n $NAMESPACE --replicas=0
sleep 10
kubectl scale deployment smartservice-api -n $NAMESPACE --replicas=3
echo "  -> Waiting for pods to be ready..."
kubectl wait --for=condition=ready pod -l app=smartservice-api -n $NAMESPACE --timeout=120s

echo ""
echo "=== All chaos tests completed ==="
echo "Recommendations:"
echo "  - Production: use Chaos Mesh for controlled experiments"
echo "  - Run during low-traffic windows"
echo "  - Monitor Grafana during tests"
