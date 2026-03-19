# =============================================================
# frontend/Dockerfile
# PURPOSE:  Containerizes the Next.js frontend
#
# NOTE:
#   In production this is NOT used — Vercel deploys directly
#   from GitHub (free, zero config).
#   This Dockerfile is for:
#   1. Local development with docker-compose
#   2. If you ever want to self-host the frontend
#   3. Migrating to AWS/Azure (they need Docker)
#
# BUILD:    docker build -t artha-frontend .
# RUN:      docker run -p 3000:3000 artha-frontend
#
# LAST UPDATED: March 2026
# =============================================================

FROM node:20-alpine

WORKDIR /app

# Install dependencies first (cached layer)
COPY package*.json ./
RUN npm ci --only=production

# Copy app code
COPY . .

# Build Next.js app
RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
