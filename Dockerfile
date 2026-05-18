FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md /app/
COPY lofin /app/lofin
RUN pip install --no-cache-dir -e ".[dashboard,dev]"
EXPOSE 8000
CMD ["uvicorn", "lofin.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
