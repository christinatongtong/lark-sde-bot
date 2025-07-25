# Use Python 3.11 slim image
FROM python:3.11-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies (including git and ping)
# RUN apt-get update && apt-get install -y iputils-ping

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

RUN npm install -g @anthropic-ai/claude-code

RUN git config --global user.email "<your-github-email>" \
    && git config --global user.name "<your-github-username>"

# Cloud Run uses PORT environment variable
EXPOSE 8080

# Run the bot
CMD ["python", "bot.py"]
