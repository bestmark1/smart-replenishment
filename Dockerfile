FROM python:3.11-slim

WORKDIR /app

# Runtime dependencies for LightGBM.
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# The package must be present before installation. Installing before copying src/
# produces an image where uvicorn cannot import smart_replenishment.
COPY pyproject.toml README.md ./
COPY src/ src/
COPY configs/ configs/
RUN pip install --no-cache-dir .

# Expose ports for both FastAPI and Streamlit
EXPOSE 8000
EXPOSE 8501
