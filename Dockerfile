FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for compiling some packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy packaging configuration and install dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .

# Copy source code and config
COPY configs/base.yaml configs/base.yaml
COPY src/ src/

# Expose ports for both FastAPI and Streamlit
EXPOSE 8000
EXPOSE 8501
