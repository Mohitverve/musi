# Use a slim Python base image
FROM python:3.9-slim

# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your source code into /app
COPY . .

# Expose the port and run the app
ENV PORT=5000
CMD ["python", "app.py"]
