# Simplified API Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY src/ ./src/

# Expose API port
EXPOSE 5000

# Run the API server with WebSocket support
CMD ["python", "src/api_server.py"]