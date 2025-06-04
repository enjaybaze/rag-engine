# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set environment variable for Python
ENV PYTHONUNBUFFERED True

# Set the working directory in the container
ENV APP_HOME /app
WORKDIR $APP_HOME

# Install system dependencies (if any are found to be needed later)
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies, including gunicorn
# We will add gunicorn to requirements.txt in a subsequent step
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port Gunicorn will run on (Cloud Run sets this via $PORT)
EXPOSE 8080

# Command to run the application using Gunicorn
# Cloud Run will automatically set the $PORT environment variable.
# The number of workers can be adjusted based on expected load and instance type.
# --timeout 0 means requests can run indefinitely (consider if your RAG processes are long)
# app:app refers to the 'app' Flask object in the 'app.py' file.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
