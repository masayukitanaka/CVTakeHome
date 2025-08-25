# Development container for PDF Insurance Analyzer
FROM python:3.11-slim-bullseye

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Build essentials
    build-essential \
    gcc \
    g++ \
    # PDF processing dependencies
    poppler-utils \
    # Development tools
    git \
    vim \
    curl \
    wget \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY docs/ ./docs/

# Create output directory
RUN mkdir -p output

# Note: .env file should be mounted as volume, not copied into image
# In production, use environment variables or secrets management

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command - can be overridden
CMD ["python", "src/pdf_insurance_analyzer.py", "--help"]

# Example usage:
# docker build -t pdf-analyzer .
# docker run -it --rm -v $(pwd)/output:/app/output -v $(pwd)/src/.env:/app/src/.env pdf-analyzer python src/pdf_insurance_analyzer.py docs/loganpark.pdf
# 
# Interactive development:
# docker run -it --rm -v $(pwd):/app pdf-analyzer /bin/bash