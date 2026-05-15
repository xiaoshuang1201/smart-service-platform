# SmartService 生产部署指南

## 前置条件

- Kubernetes 1.27+ 集群 (AKS/EKS/GKE/K3s)
- kubectl 已配置
- Helm 3.x
- cert-manager 已安装 (TLS 自动化)
- Nginx Ingress Controller 或 APISIX 已安装

## 1. 创建 Namespace 和 Secrets

```bash
# 创建命名空间
kubectl apply -f k8s/base/namespace.yaml

# 生产环境: 使用 External Secrets Operator 或 Vault
# 开发环境: 手动创建 Secrets (替换 PLACEHOLDER 为实际值)
kubectl create secret generic smartservice-secrets \
  -n smartservice \
  --from-literal=dashscope-api-key=sk-xxxxx \
  --from-literal=postgres-password=secure-password \
  --from-literal=redis-password=redis-password \
  --from-literal=api-key=production-api-key \
  --from-literal=minio-access-key=minioadmin \
  --from-literal=minio-secret-key=minioadmin
```

## 2. 部署基础设施中间件

### PostgreSQL (推荐 CloudNativePG Operator)
```bash
helm repo add cnpg https://cloudnative-pg.github.io/charts
helm install postgresql cnpg/cloudnative-pg --namespace smartservice
```

### Redis Sentinel
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install redis bitnami/redis --namespace smartservice \
  --set architecture=replication \
  --set sentinel.enabled=true
```

### Qdrant
```bash
helm install qdrant ./helm/qdrant --namespace smartservice
```

### MinIO
```bash
helm install minio bitnami/minio --namespace smartservice
```

## 3. 部署 SmartService

```bash
# Production 部署
kubectl apply -k k8s/overlays/production/

# Staging 部署
kubectl apply -k k8s/overlays/staging/

# 查看部署状态
kubectl get pods -n smartservice -w

# 验证
curl -sf https://api.smartservice.prod.example.com/api/v1/admin/health
```

## 4. 数据库初始化

```bash
kubectl exec -n smartservice deployment/smartservice-api -- \
  python scripts/init_db.py
```

## 5. 知识库迁移 (如果从 ChromaDB 迁移)

```bash
kubectl exec -n smartservice deployment/smartservice-api -- \
  python scripts/migrate_chromadb_to_qdrant.py
```

## 6. 可观测性验证

### Grafana
访问 `https://grafana.smartservice.example.com`，导入 `grafana/dashboards/smartservice-overview.json`

### Prometheus 指标
```bash
curl http://smartservice-api.smartservice:9090/metrics
```

### 告警
Prometheus 告警规则已配置在 `grafana/alerting/rules.yml`

## 7. 常见问题

**Q: Pod 启动后 CrashLoopBackOff**
```bash
kubectl logs -n smartservice deployment/smartservice-api
# 检查 DASHSCOPE_API_KEY 是否设置
# 检查 DATABASE_URL 是否可达
```

**Q: HPA 不扩缩容**
```bash
kubectl top pods -n smartservice
# 确认 metrics-server 已安装
# 检查 CPU/Memory requests 是否合理
```

**Q: Qdrant 连接失败**
```bash
kubectl exec -n smartservice deployment/smartservice-api -- \
  curl http://qdrant.smartservice:6333/health
# 确认 VECTOR_BACKEND=qdrant 在 ConfigMap 中设置
```
