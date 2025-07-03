    1 # Forcing a fresh build on Render - v2
    2 # Use the full, official Python image to ensure all system libraries are
      present
    3 FROM python:3.11
    4
    5 # Install all Camelot system dependencies, including Ghostscript and Tkinter
    6 RUN apt-get update && apt-get install -y ghostscript tk-dev python3-tk && rm -
      rf /var/lib/apt/lists/*
    7
    8 # Set the working directory
    9 WORKDIR /app
   10
   11 # Copy the requirements file
   12 COPY requirements.txt .
   13
   14 # Install Python dependencies
   15 RUN pip install --no-cache-dir -r requirements.txt
   16
   17 # Copy the rest of the application code
   18 COPY . .
   19
   20 # Set the command to run the application
   21 CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:10000"]
