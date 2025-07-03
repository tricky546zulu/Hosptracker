# Forcing a fresh build on Render - v3
# Use the full, official Python image
FROM python:3.11

# Install system dependencies and then immediately verify the installation
RUN apt-get update && \
    apt-get install -y ghostscript tk-dev python3-tk && \
    rm -rf /var/lib/apt/lists/* && \
    echo "---- Verifying Ghostscript Installation ----" && \
    which gs && \
    echo "---- Ghostscript Path Found ----"

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
