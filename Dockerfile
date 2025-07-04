# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies required for pdfplumber and other libraries
RUN apt-get update && apt-get install -y \
    pkg-config \
    libmagic-dev \
    libpoppler-cpp-dev \
    ghostscript \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code to the working directory
COPY . .

# Make port 10000 available to the world outside this container
EXPOSE 10000

# Run the application
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:10000"]
