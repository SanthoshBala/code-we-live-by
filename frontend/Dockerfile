# Stage 1: Install dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Stage 2: Build the application
FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG BACKEND_URL=http://localhost:8000
ENV BACKEND_URL=$BACKEND_URL

RUN npm run build

# Stage 3: Production runtime
FROM node:20-alpine AS runtime
WORKDIR /app

ENV NODE_ENV=production

# Copy standalone server and static assets
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
