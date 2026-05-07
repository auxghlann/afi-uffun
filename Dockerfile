# Stage 1: Build the React frontend
FROM node:20-slim AS build-frontend
WORKDIR /app/client
COPY client/package*.json ./
RUN npm install
COPY client/ ./
RUN npm run build

# Stage 2: Final image
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy server code
COPY server/app ./app
# Database will be initialized on startup (Postgres in production, SQLite fallback locally)

# Copy built frontend from Stage 1 to server's static folder
COPY --from=build-frontend /app/client/dist ./static

# Expose the port Cloud Run will provide
ENV PORT=8080
EXPOSE 8080

# Command to run the application using gunicorn for production stability
CMD gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
