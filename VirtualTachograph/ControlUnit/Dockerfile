# Use Python 3.12.1 Alpine as base image
FROM python:3.12.1-alpine

# Install bash shell
RUN apk add --no-cache bash

# Set working directory
WORKDIR /etc/usr/src/app

# Copy application code
COPY ./code /etc/usr/src/app

# Grant execution permissions to the script
RUN chmod +x /etc/usr/src/app/ControlUnitSimulator.py

# Install Python dependencies
RUN pip install --no-cache-dir requests
RUN pip install paho-mqtt

# Define the entrypoint
CMD ["python", "ControlUnitSimulator.py"]
