FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY scripts/ ./scripts/
COPY env.example ./

# Create non-root user for security
RUN useradd -r -s /bin/false webhook && \
    chown -R webhook:webhook /app

# Switch to non-root user
USER webhook

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run webhook server
CMD ["python", "scripts/webhook_handler.py"] 