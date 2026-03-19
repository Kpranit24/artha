#!/bin/bash
# =============================================================
# deploy.sh
# PURPOSE:  One-command deploy to production
#           Deploys frontend to Vercel + backend to Railway
#
# USAGE:
#   chmod +x deploy.sh
#   ./deploy.sh
#
# PREREQUISITES:
#   npm install -g vercel railway
#   vercel login
#   railway login
#
# WHAT IT DOES:
#   1. Checks all required env vars are set
#   2. Runs a quick local test
#   3. Deploys backend to Railway
#   4. Deploys frontend to Vercel
#   5. Prints the live URLs
#
# LAST UPDATED: March 2026
# =============================================================

set -e  # Stop on any error

# ── COLORS ────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'  # No Color

echo ""
echo "🚀 Artha — Deploy"
echo "================================"
echo ""

# ── CHECK PREREQS ─────────────────────────────────────────
echo "Checking prerequisites..."

if ! command -v vercel &> /dev/null; then
    echo -e "${RED}✗ Vercel CLI not found${NC}"
    echo "  Install: npm install -g vercel"
    exit 1
fi

if ! command -v railway &> /dev/null; then
    echo -e "${RED}✗ Railway CLI not found${NC}"
    echo "  Install: npm install -g @railway/cli"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo -e "${RED}✗ .env file not found${NC}"
    echo "  Run: cp .env.example .env && fill in your keys"
    exit 1
fi

# ── CHECK REQUIRED ENV VARS ───────────────────────────────
echo "Checking environment variables..."

source .env 2>/dev/null || true

MISSING=0
check_var() {
    if [ -z "${!1}" ]; then
        echo -e "  ${RED}✗ $1 is not set${NC}"
        MISSING=1
    else
        echo -e "  ${GREEN}✓ $1${NC}"
    fi
}

check_var "DATABASE_URL"
check_var "REDIS_URL"
check_var "JWT_SECRET"
check_var "CLAUDE_API_KEY"

if [ $MISSING -eq 1 ]; then
    echo ""
    echo -e "${RED}Fix the missing variables in .env before deploying.${NC}"
    exit 1
fi

echo ""

# ── QUICK LOCAL TEST ──────────────────────────────────────
echo "Running quick local test..."

cd backend
python -c "
import sys
try:
    import fastapi, uvicorn, sqlalchemy, redis, anthropic, yfinance
    print('  ✓ All Python packages installed')
except ImportError as e:
    print(f'  ✗ Missing package: {e}')
    print('  Run: pip install -r requirements.txt')
    sys.exit(1)
"
cd ..

echo ""

# ── DEPLOY BACKEND → RAILWAY ──────────────────────────────
echo "Deploying backend to Railway..."
echo -e "${YELLOW}(This takes ~2 minutes)${NC}"
echo ""

cd backend

# Link to Railway project if not already linked
if [ ! -f ".railway" ]; then
    echo "Linking to Railway project..."
    railway link
fi

# Set environment variables on Railway
echo "Setting Railway environment variables..."
while IFS= read -r line; do
    # Skip comments and empty lines
    [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
    # Skip lines without =
    [[ "$line" != *"="* ]] && continue
    # Skip empty values
    VAR_NAME="${line%%=*}"
    VAR_VAL="${line#*=}"
    [[ -z "$VAR_VAL" ]] && continue

    railway variables set "$VAR_NAME=$VAR_VAL" 2>/dev/null || true
done < ../.env

# Deploy
railway up --detach

# Get the backend URL
BACKEND_URL=$(railway domain 2>/dev/null || echo "")
if [ -z "$BACKEND_URL" ]; then
    BACKEND_URL=$(railway status 2>/dev/null | grep "Domain" | awk '{print $2}' || echo "check Railway dashboard")
fi

echo -e "${GREEN}✓ Backend deployed${NC}"
echo "  URL: https://$BACKEND_URL"

cd ..
echo ""

# ── DEPLOY FRONTEND → VERCEL ──────────────────────────────
echo "Deploying frontend to Vercel..."
echo -e "${YELLOW}(This takes ~1 minute)${NC}"
echo ""

cd frontend

# Set the backend URL in Vercel env
echo "NEXT_PUBLIC_API_URL=https://$BACKEND_URL" > .env.production

# Deploy to Vercel production
vercel --prod --yes

FRONTEND_URL=$(vercel ls --prod 2>/dev/null | head -2 | tail -1 | awk '{print $2}' || echo "check Vercel dashboard")

echo -e "${GREEN}✓ Frontend deployed${NC}"
echo "  URL: https://$FRONTEND_URL"

cd ..
echo ""

# ── HEALTH CHECK ──────────────────────────────────────────
echo "Running health check..."
sleep 5  # Wait for deploy to stabilize

if curl -sf "https://$BACKEND_URL/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${YELLOW}⚠ Backend health check failed — it may still be starting up${NC}"
    echo "  Check: https://$BACKEND_URL/health"
fi

# ── DONE ──────────────────────────────────────────────────
echo ""
echo "================================"
echo -e "${GREEN}🎉 Deployed successfully!${NC}"
echo ""
echo "  Frontend:  https://$FRONTEND_URL"
echo "  Backend:   https://$BACKEND_URL"
echo "  API docs:  https://$BACKEND_URL/docs"
echo "  Health:    https://$BACKEND_URL/health"
echo ""
echo "Next steps:"
echo "  1. Set up Supabase DB schema (docs/SETUP_GUIDE.md)"
echo "  2. Configure Telegram bot for alerts"
echo "  3. Add your custom domain in Vercel + Railway"
echo "  4. Share with your first users!"
echo ""
echo "Not financial advice. All data for informational purposes only."
