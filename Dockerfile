# Stage 1: Build the React frontend
FROM node:18-alpine AS frontend-build
WORKDIR /app/packages/marketplace-visualizer
COPY packages/marketplace-visualizer/package*.json ./
RUN npm ci
COPY packages/marketplace-visualizer/ ./
# Create the output directory that vite.config.js expects (outDir: ../magentic-marketplace/...)
RUN mkdir -p ../magentic-marketplace/src/magentic_marketplace/ui/static
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim
WORKDIR /app

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy and install the Python package
COPY packages/magentic-marketplace/ ./packages/magentic-marketplace/
RUN cd packages/magentic-marketplace && uv pip install --system -e .

# Copy the compiled frontend into where the unified server expects it
COPY --from=frontend-build /app/packages/magentic-marketplace/src/magentic_marketplace/ui/static ./packages/magentic-marketplace/src/magentic_marketplace/ui/static

# Copy experiment datasets (needed at runtime)
COPY data/ ./data/

# Runtime config
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000

EXPOSE 8000

CMD ["magentic-marketplace", "serve", "--host", "0.0.0.0", "--port", "8000"]
