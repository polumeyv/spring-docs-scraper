# Backend Dockerfile for Python scraper
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for web scraping tools
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers if needed
RUN playwright install chromium
RUN playwright install-deps

# Copy source files
COPY src/ ./src/

# Create directory for scraped docs
RUN mkdir -p /app/docs

# Expose API port
EXPOSE 8082

# Run the documentation server by default
CMD ["python", "src/serve_docs.py"]