# Use Python 3.11 slim image
FROM python:3.11-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies (including git and ping)
# RUN apt-get update && apt-get install -y iputils-ping

# Test ping (optional - remove this line if you don't need it)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Test ping (optional - remove this line if you don't need it)

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run uses PORT environment variable
EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]
