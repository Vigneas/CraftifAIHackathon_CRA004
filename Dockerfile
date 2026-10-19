# Lightweight, universally compatible Docker container
FROM python:3.10-slim

WORKDIR /app

# Install minimal OS dependencies for OpenCV (headless / container mode)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project source code & configs
COPY . .

# Run the benchmark & validation test by default
CMD ["python", "tensorrt_benchmark.py"]
