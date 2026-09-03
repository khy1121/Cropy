# CropCare AI - Frontend (Next.js 15, standalone 출력)

FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# BACKEND_ORIGIN은 반드시 "빌드 시점"에 주어야 한다.
# output:standalone 은 next.config.js를 산출물에 포함하지 않고, rewrite 목적지를
# .next/required-server-files.json 에 문자열로 굳혀 넣는다. 따라서 런타임
# 환경변수로 주면 조용히 무시되고 기본값(127.0.0.1:8000)으로 프록시를 시도해
# 컨테이너 안에서 연결이 거부된다 — API와 /uploads 이미지가 모두 깨진다.
ARG BACKEND_ORIGIN=http://backend:8000
ENV BACKEND_ORIGIN=${BACKEND_ORIGIN}

# NEXT_PUBLIC_* 도 빌드 시점에 클라이언트 번들에 박힌다.
# 빈 값으로 두면 API 호출이 프론트와 같은 오리진으로 나가고, 위 rewrite가
# 백엔드로 프록시한다 → 브라우저가 백엔드를 직접 부르지 않으므로 CORS 설정이
# 필요 없고, /uploads 상대경로 이미지도 같은 경로로 해결된다.
ENV NEXT_PUBLIC_API_URL=""

RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup -S nodejs && adduser -S nextjs -G nodejs

COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
