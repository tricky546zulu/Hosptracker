import logging
from app import app
from routes import *
from scheduler import start_scheduler

# Configure logging
logging.basicConfig(level=logging.INFO)

# Start the scheduler when the app starts
with app.app_context():
    start_scheduler()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)