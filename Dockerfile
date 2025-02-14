# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Install FFmpeg and other OS-level dependencies
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port (Railway sets PORT environment variable)
EXPOSE 5000

# Use Gunicorn to serve the Flask app
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
