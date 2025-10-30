FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY meshtastic_downloader.py .
COPY config.yaml .

# Create volume for state file
VOLUME ["/app/data"]

# Run the application
CMD ["python", "-u", "meshtastic_downloader.py"]
