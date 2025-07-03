# Use the official Render Python image
FROM render/python:3

# Install Ghostscript
RUN apt-get update && apt-get install -y ghostscript

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY . .

# Command to run the application
CMD ["gunicorn", "main:app"]
