# ---- frontend build stage ----
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_BASE_URL=""
RUN npm run build

# ---- backend + final image ----
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
# Install the CPU-only torch wheel first: the default PyPI wheel bundles CUDA
# libraries that are unused here but nearly double the memory footprint,
# which is enough to blow a 512MB Render free-tier instance at startup.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY server/ server/
COPY data/ data/

# Build the embedding index at image build time so the container is self-contained.
RUN python -m src.ingest

COPY --from=frontend-build /app/frontend/dist ./frontend/dist

ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn server.main:app --host 0.0.0.0 --port ${PORT}"]
