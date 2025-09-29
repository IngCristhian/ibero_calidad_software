FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Create empty directories for logs and reports (content will be generated at runtime)
RUN mkdir -p logs reports

# Create non-root user for security
RUN useradd -m -u 1000 therac && \
    chown -R therac:therac /app
USER therac

# Environment variables - Always buggy version for educational purposes
ENV VERSION=buggy
ENV DEBUG_MODE=true
ENV SIMULATION_SPEED=1x

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/status || exit 1

# Expose port for web interface
EXPOSE 8080

# Default command - Run web interface to demonstrate bugs
CMD ["python", "src/web_interface/app.py"]