FROM python:3.11-slim

WORKDIR /app

# Enable GenAI tracing (must be set before SDK import)
ENV AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING=true

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000

CMD ["gunicorn", "app.main:app", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120"]
