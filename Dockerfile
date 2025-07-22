# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set permissions and create temporary directory
RUN chmod +x /app/app.py && \
    mkdir -p /tmp/svg_processing && \
    chown -R www-data:www-data /tmp/svg_processing

# Switch to a non-root user
USER www-data

# Expose port
EXPOSE 8877

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8877/health || exit 1

# Start Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8877", "--workers", "4", "app:app"]
