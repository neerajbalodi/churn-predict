# Code-only image. The model is NOT baked in — it's downloaded from S3
# at startup. This decouples code deploys from model updates.
FROM python:3.12-slim

WORKDIR /app

# Install deps first so this layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the serving code and tests — no training inside the image.
COPY app.py test_app.py ./

EXPOSE 8000

# 2 workers is plenty for a classroom; tune for real load.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
