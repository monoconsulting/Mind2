# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entrypoint script and make it executable
COPY backend/entrypoint.sh .
RUN chmod +x ./entrypoint.sh

# Copy the rest of the backend source code
COPY backend/src/ .

# Expose the port the app runs on
EXPOSE 5000

# Run the entrypoint script
ENTRYPOINT ["./entrypoint.sh"]
