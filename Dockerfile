# Use an official, public Python image
FROM python:3.11-slim

# Install Ghostscript
RUN apt-get update && apt-get install -y ghostscript

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set the command to run the application
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:10000"]
