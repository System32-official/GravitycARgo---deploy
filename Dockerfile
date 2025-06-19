FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_ENV=production
ENV DEBUG=False

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install gunicorn for production
RUN pip install gunicorn

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads container_plans logs static/uploads serving

# Create .gitkeep files to ensure directories are preserved
RUN touch uploads/.gitkeep container_plans/.gitkeep logs/.gitkeep

# Expose port (Render will set this dynamically)
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start command using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "300", "--max-requests", "1000", "wsgi:app"]

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:$PORT/ || exit 1

# Use gunicorn for production
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 300 --max-requests 1000 --max-requests-jitter 50 wsgi:app
