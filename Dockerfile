# Single-stage, slim base. We train the model at BUILD time so the image is
# self-contained — the container needs no data and no network to serve.
# (In a real system you'd train in CI and COPY the artifact in; baking it here
#  keeps the teaching repo to one moving part.)
FROM python:3.12-slim

WORKDIR /app

# Install deps first so this layer caches across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source and produce model.joblib inside the image.
COPY train.py app.py ./
RUN python train.py

EXPOSE 8000

# 2 workers is plenty for a classroom; tune for real load.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
