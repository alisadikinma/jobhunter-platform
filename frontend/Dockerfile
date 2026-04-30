FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install --legacy-peer-deps

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Ensure public/ exists even when git doesn't track an empty dir — the runner
# stage COPYs /app/public unconditionally, so a missing dir fails the build.
RUN mkdir -p public
# NEXT_PUBLIC_* vars are baked into the client bundle at build time. The
# `args:` block in docker-compose.yml passes the production URL, but it must
# be ARG'd here so Docker exposes it to the build, then ENV'd so Next.js
# substitutes process.env.NEXT_PUBLIC_API_URL inside the bundle. Without this
# the fallback `http://localhost:8000` ships to browsers and POST /api/auth/login
# fails as mixed-content from an https page.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup -g 1001 -S nodejs && adduser -S nextjs -u 1001

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.ts ./next.config.ts

USER nextjs
EXPOSE 3000
CMD ["npm", "run", "start"]
