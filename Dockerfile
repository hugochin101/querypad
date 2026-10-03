# Stage 1: build the React frontend
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python API that also serves the built frontend
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/dist ./static
RUN mkdir -p /app/seed && python scripts/make_sample_data.py 500000 /app/seed/bike_trips.csv
ENV QUERYPAD_DATA_DIR=/data \
    QUERYPAD_STATIC_DIR=/app/static \
    QUERYPAD_SEED_CSV=/app/seed/bike_trips.csv
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
