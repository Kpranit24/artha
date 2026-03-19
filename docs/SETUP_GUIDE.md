# Setup Guide — Run in 5 Minutes

## Prerequisites
- Node.js 18+
- Python 3.12+
- Docker + Docker Compose (for full stack)
- Git

---

## Option A — Full stack with Docker (recommended)

### 1. Clone and configure
```bash
git clone https://github.com/your-username/artha
cd artha

# Copy env file and fill in your keys
cp .env.example .env
```

### 2. Edit .env — minimum required keys
```bash
# REQUIRED — generate a random string:
JWT_SECRET=your-random-64-char-secret-here

# REQUIRED for AI insights:
CLAUDE_API_KEY=sk-ant-your-key-here

# OPTIONAL — leave empty to use free tiers:
COINGECKO_API_KEY=
ALPHA_VANTAGE_KEY=
NEWSAPI_KEY=

# OPTIONAL — for Telegram alerts:
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

### 3. Start everything
```bash
docker-compose up
```

### 4. Open the app
- Dashboard: http://localhost:3000
- API docs:  http://localhost:8000/docs
- Health:    http://localhost:8000/health

---

## Option B — Run services separately (development)

### Backend
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure env
cp ../.env.example .env
# Edit .env with your keys

# Start Redis (required)
docker run -d -p 6379:6379 redis:7-alpine

# Start FastAPI
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Copy env
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start Next.js
npm run dev
```

---

## Deploy to production

### Frontend → Vercel (free, 2 minutes)
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy from frontend directory
cd frontend
vercel --prod

# Set environment variable in Vercel dashboard:
# NEXT_PUBLIC_API_URL = https://your-railway-backend.railway.app
```

### Backend → Railway (~5 minutes)
```
1. Go to railway.app → New Project → Deploy from GitHub
2. Select your repo → select /backend as root directory
3. Railway auto-detects Dockerfile and builds
4. Add environment variables in Railway dashboard (copy from .env)
5. Your API will be at: https://your-app.railway.app
```

### Database → Supabase (free)
```
1. Go to supabase.com → New Project → choose ap-south-1 (Singapore)
2. Go to SQL editor → paste contents of:
   backend/app/db/migrations/001_initial_schema.sql
3. Run the SQL
4. Get DATABASE_URL from Settings → Database
5. Update RAILWAY env var: DATABASE_URL = your Supabase URL
```

### Cache → Upstash Redis (free)
```
1. Go to upstash.com → Create Database → choose ap-south-1
2. Copy REDIS_URL from dashboard
3. Update RAILWAY env var: REDIS_URL = your Upstash URL
```

---

## Verify everything is working

```bash
# 1. Health check
curl https://your-api.railway.app/health
# Expected: {"status": "ok", "services": {"cache": "ok", "database": "ok"}}

# 2. Heatmap data
curl "https://your-api.railway.app/api/heatmap?index=crypto&timeframe=1d"
# Expected: {"success": true, "data": {"bubbles": [...], ...}}

# 3. WebSocket (use wscat)
npm install -g wscat
wscat -c "wss://your-api.railway.app/ws/prices/test123?symbols=BTC,ETH"
# Expected: {"event": "connected", ...} then price updates every 15s
```

---

## Common issues

### "Redis connection refused"
```bash
# Make sure Redis is running
docker ps | grep redis
# If not running:
docker-compose up redis
```

### "CoinGecko rate limited"
```
Normal — free tier is 30 req/min
App automatically falls back to cached data
Resumes in ~60 seconds
Set DEMO_MODE=true in .env to use static data during development
```

### "CLAUDE_API_KEY not set"
```
AI insights disabled but everything else works
Set ENABLE_AI_INSIGHTS=false in .env to silence the warning
```

### "yfinance returns empty data"
```
NSE data has occasional delays — this is normal
yfinance is unofficial and may be slow for some tickers
The static_demo.py fallback handles this automatically
```

### Frontend can't reach backend
```bash
# Check NEXT_PUBLIC_API_URL in frontend/.env.local
# Must match your backend URL exactly (no trailing slash)
echo $NEXT_PUBLIC_API_URL
```

---

## Cost summary

| Service          | Free tier          | When to upgrade         |
|------------------|--------------------|-------------------------|
| Vercel           | 100GB/mo bandwidth | At 10K+ daily users     |
| Railway          | Need $5/mo starter | From day 1 (always-on)  |
| Supabase         | 500MB, 50K users   | At 50K monthly users    |
| Upstash Redis    | 10K commands/day   | At ~500 daily users     |
| CoinGecko        | 30 req/min         | At 2K+ daily users      |
| Claude API       | Pay per use ~$3/day| Scale with usage        |
| **Total**        | **~$5-6/mo**       | ~$30/mo at 1K users     |
