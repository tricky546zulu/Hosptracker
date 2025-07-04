from apscheduler.schedulers.background import BackgroundScheduler
from pdf_scraper import run_scraping
from datetime import datetime, timedelta

def start_scheduler(app):
    """Initializes and starts the scraping scheduler."""
    scheduler = BackgroundScheduler(daemon=True)

    # Schedule the main job to run every 2 hours
    scheduler.add_job(
        run_scraping,
        'interval',
        hours=2,
        id='hospital_data_scraping',
        replace_existing=True,
        args=[app]  # Pass the app context
    )

    # Schedule an initial job to run 10 seconds after startup
    run_date = datetime.now() + timedelta(seconds=10)
    scheduler.add_job(
        run_scraping,
        'date',
        run_date=run_date,
        id='initial_scraping',
        replace_existing=True,
        args=[app]  # Pass the app context
    )

    scheduler.start()
    print("Hospital data scraping scheduler started")
