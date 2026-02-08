# Use official Python lightweight image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Chromium and Media (FFmpeg)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    ffmpeg \
    chromium \
    chromium-driver \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for DrissionPage / Chromium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_PATH=/usr/lib/chromium/
ENV DISPLAY=:99

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create data directory for persistence
RUN mkdir -p /app/data /app/scripts /app/logs

# Expose the dashboard port
EXPOSE 5000

# Start command: Use xvfb-run to simulate a display for the browser-based features
CMD ["xvfb-run", "--server-args=-screen 0 1920x1080x24", "python", "main.py"]
