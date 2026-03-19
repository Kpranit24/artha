# Migration Guide — Moving Between Cloud Providers

## Overview
This app is fully Docker-containerized. Migrating between providers
means changing ONE file (.env) and updating your DNS record.
Zero code changes required.

Total time: ~35 minutes

---

## Before any migration

### 1. Backup the database (5 minutes)
```bash
# Get your current DATABASE_URL from .env
# Then run:
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M).sql

# Verify backup is valid:
wc -l backup_*.sql   # Should be > 100 lines
```

### 2. Note your current env vars
```bash
# Print all env var NAMES (not values — don't expose secrets)
cat .env | grep "=" | cut -d"=" -f1
```

### 3. Keep old service running
DO NOT shut down the old service until the new one is confirmed healthy.
Cloudflare DNS switchover is instant — you can rollback in 30 seconds.

---

## Railway → AWS ECS

### Step 1: Build and push Docker image (10 minutes)
```bash
# Build
docker build -t artha-backend ./backend
docker build -t artha-frontend ./frontend

# Tag for AWS ECR
docker tag artha-backend 123456789.dkr.ecr.ap-south-1.amazonaws.com/artha-backend:latest
docker tag artha-frontend 123456789.dkr.ecr.ap-south-1.amazonaws.com/artha-frontend:latest

# Push (login first: aws ecr get-login-password | docker login ...)
docker push 123456789.dkr.ecr.ap-south-1.amazonaws.com/artha-backend:latest
docker push 123456789.dkr.ecr.ap-south-1.amazonaws.com/artha-frontend:latest
```

### Step 2: Create AWS services (10 minutes)
```
AWS Console:
1. RDS → Create PostgreSQL 15 instance (db.t3.micro = ~$15/mo)
2. ElastiCache → Create Redis 7 cluster (cache.t3.micro = ~$15/mo)
3. ECS → Create cluster → Create service using your ECR images
4. Set environment variables in ECS task definition
```

### Step 3: Update .env (2 minutes)
```bash
# Only these lines change:
DATABASE_URL=postgresql://user:pass@new-rds-host.amazonaws.com:5432/artha
REDIS_URL=redis://new-elasticache-host.cache.amazonaws.com:6379
API_URL=https://new-api.arthafinance.in
```

### Step 4: Restore database (5 minutes)
```bash
psql $NEW_DATABASE_URL < backup_20260319.sql
```

### Step 5: Verify new deployment
```bash
# Check health endpoint
curl https://new-api.arthafinance.in/health
# Should return: {"status": "ok", ...}

# Test one API call
curl "https://new-api.arthafinance.in/api/heatmap?index=crypto&timeframe=1d"
```

### Step 6: Switch DNS (2 minutes)
```
Cloudflare Dashboard:
1. Go to DNS settings for arthafinance.in
2. Change A record to point to new AWS IP
3. Set TTL to 60 seconds (fast propagation)
4. Propagates in ~60 seconds globally
```

### Step 7: Monitor for 30 minutes
```bash
# Watch logs
aws logs tail /ecs/artha-backend --follow

# Check health every 30s
watch -n 30 curl -s https://api.arthafinance.in/health | python -m json.tool
```

### Step 8: Shut down Railway
Only after 30 minutes of stable traffic on AWS.

---

## Railway → Azure Container Apps

Same steps, different commands:

```bash
# Push to Azure Container Registry
docker tag artha-backend artharegistry.azurecr.io/artha-backend:latest
az acr push artharegistry.azurecr.io/artha-backend:latest

# Create Azure services:
# - Azure Database for PostgreSQL (~$15/mo)
# - Azure Cache for Redis (~$15/mo)
# - Azure Container Apps (pay per use, ~$5-10/mo)

# Update .env with Azure connection strings
DATABASE_URL=postgresql://user:pass@new-azure-postgres.postgres.database.azure.com:5432/artha
REDIS_URL=rediss://artha-redis.redis.cache.windows.net:6380,password=xxx,ssl=True
```

---

## Railway → DigitalOcean App Platform

Simplest migration — DigitalOcean reads directly from GitHub:

```
1. Create new app in DigitalOcean App Platform
2. Connect same GitHub repo
3. Add environment variables in DigitalOcean dashboard
4. Deploy (auto-builds from Dockerfile)
5. Update DNS
```

Cost: $12/mo (512MB RAM) vs Railway $5/mo
Trade-off: Simpler, more generous free bandwidth

---

## Rollback procedure (if something breaks)

```
1. Cloudflare → change DNS back to old IP (30 seconds)
2. All traffic immediately goes back to old service
3. Old service is still running — zero downtime
4. Investigate the issue on new provider
5. Try again when fixed
```

---

## What NEVER changes between providers

- All application code
- Dockerfile
- docker-compose.yml structure
- Database schema
- API response shapes
- Frontend code
- TypeScript types

## What changes between providers

- .env connection strings (DATABASE_URL, REDIS_URL)
- DNS A record in Cloudflare
- Provider dashboard setup
- Monthly invoice recipient
