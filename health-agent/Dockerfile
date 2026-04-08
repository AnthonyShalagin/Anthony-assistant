FROM python:3.11-slim

# Security: create non-root user
RUN groupadd -r agent && useradd -r -g agent -d /app -s /sbin/nologin agent

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create writable data directory (for SQLite)
RUN mkdir -p /app/data && chown -R agent:agent /app/data

# Switch to non-root user
USER agent

# No exposed ports — Telegram uses outbound polling only
# Health check via database accessibility
HEALTHCHECK --interval=5m --timeout=10s --retries=3 \
    CMD python -c "from database import init_db; init_db(); print('OK')"

CMD ["python", "main.py"]
