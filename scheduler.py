import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pdf_scraper import run_scraping

scheduler = None

def start_scheduler():
    """Start the background scheduler for automatic data updates"""
    global scheduler
    
    if scheduler is None:
        scheduler = BackgroundScheduler()
        
        # Schedule scraping every 30 minutes
        scheduler.add_job(
            func=run_scraping,
            trigger=IntervalTrigger(minutes=30),
            id='hospital_data_scraping',
            name='Hospital Data Scraping',
            replace_existing=True
        )
        
        # Run initial scraping after 10 seconds
        scheduler.add_job(
            func=run_scraping,
            trigger='date',
            id='initial_scraping',
            name='Initial Hospital Data Scraping'
        )
        
        scheduler.start()
        logging.info("Hospital data scraping scheduler started")

def stop_scheduler():
    """Stop the scheduler"""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        scheduler = None
        logging.info("Scheduler stopped")