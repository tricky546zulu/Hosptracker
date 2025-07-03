from apscheduler.schedulers.background import BackgroundScheduler
from pdf_scraper import run_scraping
import logging

# Set up logging for APScheduler
logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.INFO)

# Import app here, but be careful to avoid circular imports
# We will pass the app instance to the scheduler functions
# from main.py to ensure it has access to the context.

scheduler = BackgroundScheduler()

def start_scheduler(app_instance):
    """
    Starts the APScheduler to run the hospital data scraping job.
    """
    print("Hospital data scraping scheduler started")

    # Add the initial scraping job to run immediately
    # Wrap run_scraping in a function that provides the app context
    def run_scraping_with_context():
        with app_instance.app_context():
            run_scraping()

    scheduler.add_job(
        run_scraping_with_context,
        'date',
        run_date='now',
        id='initial_scraping',
        name='Initial Hospital Data Scraping'
    )

    # Schedule the job to run every 12 hours
    scheduler.add_job(
        run_scraping_with_context,
        'interval',
        hours=12,
        id='hospital_data_scraping',
        name='Hospital Data Scraping'
    )

    scheduler.start()
