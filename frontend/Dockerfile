FROM node:22-slim AS base

WORKDIR /app

RUN corepack enable

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

EXPOSE 3000

FROM base AS dev
CMD ["pnpm", "dev", "-H", "0.0.0.0", "-p", "3000"]

FROM base AS prod
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN pnpm build
CMD ["pnpm", "start"]
