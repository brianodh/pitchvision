# PitchVision web app (Next.js) container.
# Runs the Next.js production server on port 3000.
# Needs yt-dlp + ffmpeg on PATH for link analysis (POST /api/analyze-url).
#
#   docker build -f web/Dockerfile -t pitchvision-web .
#   docker run -p 3000:3000 \
#     -e PV_BACKEND_URL=http://backend:8000 \
#     -e PV_BACKEND_TOKEN=yourtoken \
#     pitchvision-web
#

FROM node:22-slim AS builder

WORKDIR /app/web

# System deps needed to build yt-dlp's native deps and ffmpeg probe
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# yt-dlp binary for downloading video links
RUN pip install --break-system-packages --no-cache-dir yt-dlp

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ .
RUN npm run build

# ---------------------------------------------------------------
# Runtime stage
# ---------------------------------------------------------------
FROM node:22-slim

WORKDIR /app/web

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --break-system-packages --no-cache-dir yt-dlp

# Copy built app from builder
COPY --from=builder /app/web/.next .next
COPY --from=builder /app/web/public public
COPY --from=builder /app/web/node_modules node_modules
COPY --from=builder /app/web/package.json package.json
COPY --from=builder /app/web/scripts scripts

ENV NODE_ENV=production
ENV PORT=3000
EXPOSE 3000

# dataDir() defaults to <cwd>/data; uploads/jobs/matches live there.
VOLUME /app/web/data

CMD ["npm", "start"]
