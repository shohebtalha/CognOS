FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md* ./
COPY src ./src
RUN pip install --no-cache-dir -e .
EXPOSE 8420
CMD ["python", "-m", "cogn_os.api.server"]
