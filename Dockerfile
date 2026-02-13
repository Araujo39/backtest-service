FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create reports directory
RUN mkdir -p reports

# Expose port (Railway usa a variável PORT)
EXPOSE 8080

# Run FastAPI server
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}
