# Artha — Free AI-Powered Market Dashboard

> India-first, AI-powered, open-source market dashboard.
> Built for people who can't afford $20-200/month subscriptions.

---

## What this is
A full-stack finance dashboard covering Indian stocks (NSE/BSE),
US equities, and crypto — with Claude AI powering the insight layer.

## What it costs to run
~$5-10/month. Compare to Perplexity Finance at $20-200/month.

## Tech stack
- Frontend  → Next.js 15 + TypeScript + Plotly.js + Tailwind
- Backend   → FastAPI (Python 3.12) + LangGraph agents
- Database  → Supabase (Postgres) — free tier
- Cache     → Upstash Redis — free tier
- AI        → Claude API (claude-sonnet) — pay per use ~$3-5/day
- Deploy    → Vercel (frontend) + Railway (backend)

---

## Quick start (local dev)

### Prerequisites
- Node.js 18+
- Python 3.12+
- Docker + Docker Compose

### 1. Clone and setup
```bash
git clone https://github.com/your-username/artha
cd artha
cp .env.example .env
# Fill in your API keys in .env
```

### 2. Run everything with Docker
```bash
docker-compose up
```

### 3. Or run services separately
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

---

## Project structure
```
/
├── frontend/          Next.js app — what users see
├── backend/           FastAPI — data, agents, AI
├── infrastructure/    Docker, nginx configs
├── docs/              Architecture, upgrade guides
└── .env.example       All environment variables documented
```

---

## Environment variables
See `.env.example` — every variable is documented with:
- What it does
- Where to get it
- Free vs paid options
- What breaks if it's missing

---

## Deployment

### Free tier (recommended to start)
- Frontend → Vercel (free)
- Backend  → Railway ($5/mo)
- DB       → Supabase (free)
- Cache    → Upstash Redis (free)

### Migrating between cloud providers
See `docs/MIGRATION_GUIDE.md` — Docker makes this ~35 minutes.
Only the `.env` file changes. Zero code changes needed.

---

## AI monitoring
5 agents watch the app 24/7:
- frontend_agent  → page load, chart errors, bundle size
- backend_agent   → response times, API failures, memory
- db_agent        → storage, slow queries, backups
- security_agent  → rate abuse, JWT anomalies, exposed keys
- cost_agent      → API spend, free tier usage, forecasts

Alerts sent to Telegram. Daily report at 9am IST.
See `docs/MONITORING.md`

---

## Data sources (all free)
| Market        | Source          | Limit              | Paid upgrade       |
|---------------|-----------------|--------------------|--------------------|
| Crypto        | CoinGecko       | 30 req/min         | Pro $129/mo        |
| US stocks     | Yahoo Finance   | Unofficial         | Polygon $199/mo    |
| India stocks  | NSE + yfinance  | 1min delay         | Twelve Data $39/mo |
| News          | NewsAPI + RSS   | 100 req/day        | NewsAPI $449/mo    |

---

## Notes for future developers
Every file in this codebase has:
- A header explaining what it does
- Free tier limits and upgrade paths
- Which AI agent monitors it
- Last reviewed date

When you add a new file, copy the template from `docs/FILE_TEMPLATE.md`

---

## Roadmap
- [x] Project scaffold
- [ ] Backend data agents (CoinGecko, Yahoo, NSE)
- [ ] FastAPI endpoints
- [ ] Frontend charts (Plotly bubble heatmap)
- [ ] Claude insight agent
- [ ] Portfolio tracker
- [ ] Auth (Supabase)
- [ ] AI monitoring agents
- [ ] Telegram alerts
- [ ] Production deploy

---

## Contributing
This is built to be free for everyone.
If you improve it, please PR back so others benefit too.

---

*Not financial advice. All data for informational purposes only.*
