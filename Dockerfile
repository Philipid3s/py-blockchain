FROM python:3.11-slim

# Create non-root user for security
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

# Install dependencies first (layer cache friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Persistent volume for SQLite database
RUN mkdir -p /data && chown app:app /data
VOLUME ["/data"]

# Run as non-root
USER app

ENV DB_PATH=/data/blockchain.db
ENV BASE_URL=http://localhost:8000
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Single worker — required because blockchain state is in-memory between DB loads
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--timeout", "120", "app:app"]
