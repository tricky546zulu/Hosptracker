# Forcing a fresh build on Render - v2
# Use the full, official Python image to ensure all system libraries are present
FROM python:3.11

# Install all Camelot system dependencies, including Ghostscript and Tkinter
RUN apt-get update && apt-get install -y ghostscript tk-dev python3-tk && rm -
      rf /var/lib/apt/lists/*

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
