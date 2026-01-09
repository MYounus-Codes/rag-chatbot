# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install playwright browsers if needed
RUN playwright install --with-deps chromium

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p .chainlit .files

# Expose port
EXPOSE 8080

# Set environment variables
ENV CHAINLIT_HOST=0.0.0.0
ENV CHAINLIT_PORT=8080

# Run the application
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8080"]
