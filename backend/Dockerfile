# Use Ubuntu base image which has better package availability
FROM ubuntu:22.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set the working directory in the container
WORKDIR /app

# Install Python and system dependencies for PaddleOCR
RUN apt-get update && apt-get install -y \
    python3 \
    python3-dev \
    python3-pip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libglu1-mesa \
    libxi6 \
    libxrandr2 \
    libxss1 \
    libxcursor1 \
    libxcomposite1 \
    libasound2 \
    libxdamage1 \
    libxtst6 \
    libatspi2.0-0 \
    libgtk-3-0 \
    libdrm2 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for python - use default Python 3.10
RUN ln -s /usr/bin/python3 /usr/bin/python

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entrypoint script and make it executable
COPY backend/entrypoint.sh .
RUN sed -i 's/\r$//' ./entrypoint.sh && chmod +x ./entrypoint.sh

# Copy the rest of the backend source code
COPY backend/src/ .

# Copy database migrations
COPY database/migrations/ /app/database/migrations/

# Expose the port the app runs on
EXPOSE 5000

# Run the entrypoint script
ENTRYPOINT ["./entrypoint.sh"]
