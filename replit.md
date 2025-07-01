# Saskatchewan Hospital Monitor

## Overview

This is a Flask-based web application that automatically scrapes and monitors Emergency Department patient data from Saskatchewan hospitals. The system extracts data from PDF reports published by eHealth Saskatchewan and provides a real-time dashboard with historical tracking capabilities.

## System Architecture

**Backend Framework**: Flask with SQLAlchemy ORM
- Simple web server handling API endpoints and template rendering
- Background scheduler for automated data collection
- PDF scraping using Camelot library for table extraction

**Frontend**: Bootstrap-based responsive web interface
- Real-time dashboard showing current hospital capacity
- Historical data visualization with Chart.js
- Auto-refreshing data display with manual refresh option

**Data Storage**: SQLAlchemy with configurable database backend
- Designed to work with any SQL database supported by SQLAlchemy
- Currently configured to use DATABASE_URL environment variable
- Models support PostgreSQL, MySQL, SQLite, and other SQL databases

## Key Components

### Core Application (`app.py`, `main.py`)
- Flask application factory with database initialization
- Session management with configurable secret key
- Database connection pooling and health checks
- Automatic table creation on startup

### Data Models (`models.py`)
- **HospitalCapacity**: Stores patient count data for each hospital
- **ScrapingLog**: Tracks scraping attempts and results for monitoring

### PDF Scraper (`pdf_scraper.py`)
- Uses Camelot library to extract tables from PDF reports
- Handles Emergency Department data extraction specifically
- Maps hospital codes to full names (RUH, SPH, SCH, JPCH)
- Error handling and logging for failed scraping attempts

### Scheduler (`scheduler.py`)
- APScheduler background service for automated data collection
- Runs scraping every hour with initial run after 10 seconds
- Graceful start/stop functionality

### Web Interface (`routes.py`, `templates/`)
- Dashboard route serving real-time hospital data
- Historical data visualization page
- REST API endpoint for hospital capacity data
- Cache-busting headers for real-time updates

### Frontend Assets
- Bootstrap dark theme with custom Saskatchewan hospital styling
- Chart.js for data visualization
- Feather icons for consistent UI elements
- Responsive design for mobile and desktop

## Data Flow

1. **Automated Scraping**: Background scheduler triggers PDF scraping every hour
2. **PDF Processing**: Camelot extracts table data from eHealth Saskatchewan PDF
3. **Data Storage**: Hospital capacity data saved to database with timestamps
4. **API Access**: Frontend requests current data via REST API
5. **Dashboard Update**: Real-time display of latest hospital patient counts
6. **Historical Analysis**: Time-series visualization of patient trends

## External Dependencies

### Required Python Packages
- Flask and Flask-SQLAlchemy for web framework and ORM
- Camelot-py for PDF table extraction
- APScheduler for background task scheduling
- Requests for HTTP operations

### External Data Source
- eHealth Saskatchewan PDF reports (https://www.ehealthsask.ca/reporting/Documents/SaskatoonHospitalBedCapacity.pdf)
- Updates every 15 minutes from the source
- Automated extraction of Emergency Department patient counts

### Frontend Libraries
- Bootstrap 5.3 with dark theme
- Chart.js with date adapters for time-series visualization
- Feather Icons for UI consistency
- Font Awesome for additional icons

## Deployment Strategy

**Environment Configuration**:
- `DATABASE_URL`: Database connection string (required)
- `SESSION_SECRET`: Flask session encryption key (defaults to dev key)

**Database Setup**:
- Automatic table creation on application startup
- SQLAlchemy migrations can be added for production deployments
- Connection pooling configured for reliability

**Hosting Requirements**:
- Python 3.8+ environment
- Access to external PDF URL for scraping
- Persistent database storage
- Background task support for scheduler

**Monitoring**:
- ScrapingLog model tracks all scraping attempts
- Application logging for debugging and monitoring
- Error handling with graceful degradation

## Changelog

- July 01, 2025. Initial setup

## User Preferences

Preferred communication style: Simple, everyday language.