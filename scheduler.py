import logging
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from pdf_scraper import run_scraping

scheduler = None

def start_scheduler():
    """Start the background scheduler for automatic data updates"""
    global scheduler
    
    if scheduler is not None:
        logging.info("Scheduler already running")
        return
    
    try:
        scheduler = BackgroundScheduler()
        
        # Schedule scraping every 30 minutes
        scheduler.add_job(
            func=run_scraping,
            trigger="interval",
            minutes=30,
            id='hospital_data_scraping',
            name='Hospital Data Scraping',
            replace_existing=True
        )
        
        # Run initial scraping
        scheduler.add_job(
            func=run_scraping,
            trigger="date",
            id='initial_scraping',
            name='Initial Hospital Data Scraping',
            replace_existing=True
        )
        
        scheduler.start()
        logging.info("Scheduler started - hospital data will be updated every 30 minutes")
        
        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())
        
    except Exception as e:
        logging.error(f"Error starting scheduler: {str(e)}")

def stop_scheduler():
    """Stop the scheduler"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logging.info("Scheduler stopped")
