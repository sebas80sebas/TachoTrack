# Use Python 3.12.1 Alpine as base image for a lightweight container
FROM python:3.12.1-alpine

# Install bash shell for scripting support
RUN apk add --no-cache bash

# Set the working directory inside container
WORKDIR /etc/usr/src/app

# Copy application source code into container
COPY ./code /etc/usr/src/app

# Grant execution permissions to the GNSS simulator script
RUN chmod +x /etc/usr/src/app/GNSSSimulator.py

# Install Python package dependencies
RUN pip install --no-cache-dir requests

# Define the container entry point
# Starts the GNSS Simulator when container launches
CMD ["python", "GNSSSimulator.py"]
