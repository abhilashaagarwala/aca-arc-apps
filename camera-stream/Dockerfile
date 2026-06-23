FROM python:3.12-slim

# OpenCV (headless) runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV PORT=8080
ENV CAMERA_DEVICE=/dev/video0
EXPOSE 8080

# gthread worker streams MJPEG well; timeout 0 keeps long-lived stream connections alive
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "app:app"]
