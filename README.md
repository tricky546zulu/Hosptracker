# Saskatchewan Hospital Emergency Department Monitor

A real-time monitoring system for Emergency Department patient counts across Saskatchewan hospitals. The system automatically scrapes data from eHealth Saskatchewan PDF reports and provides a clean web interface for viewing current and historical data.

## Features

- **Real-time Data**: Automatically extracts patient counts from official eHealth Saskatchewan PDF reports
- **Multiple Hospitals**: Monitors Royal University Hospital, St. Paul's Hospital, Saskatoon City Hospital, and Jim Pattison Children's Hospital
- **Historical Tracking**: Stores and displays historical data with trend analysis
- **Responsive Design**: Clean, mobile-friendly interface with dark theme
- **Data Validation**: Filters out anomalies and validates data for accuracy
- **Weather Integration**: Shows current Saskatoon weather conditions

## Technology Stack

- **Backend**: Python Flask with SQLAlchemy
- **Data Extraction**: Camelot for PDF table extraction
- **Database**: SQLite (default) or PostgreSQL
- **Frontend**: Bootstrap 5 with Chart.js for visualizations
- **Scheduling**: APScheduler for automated data collection
- **Deployment**: Gunicorn WSGI server

## Installation

### Prerequisites

- Python 3.11+
- pip or uv package manager

### Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd saskatchewan-hospital-monitor
   ```

2. **Install dependencies**:
   ```bash
   # Using pip
   pip install -r requirements.txt
   
   # Or using uv (recommended)
   uv sync
   ```

3. **Set up environment variables** (optional):
   ```bash
   # Create .env file
   echo "DATABASE_URL=sqlite:///hospitals.db" > .env
   echo "SESSION_SECRET=your-secret-key-here" >> .env
   echo "OPENWEATHERMAP_API_KEY=your-api-key" >> .env
   ```

4. **Initialize the database**:
   ```bash
   python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

5. **Run the application**:
   ```bash
   # Development
   python main.py
   
   # Production
   gunicorn --bind 0.0.0.0:5000 main:app
   ```

## Configuration

### Environment Variables

- `DATABASE_URL`: Database connection string (default: SQLite)
- `SESSION_SECRET`: Flask session secret key
- `OPENWEATHERMAP_API_KEY`: API key for weather data (optional)

### Database Options

**SQLite (Default)**:
```
DATABASE_URL=sqlite:///hospitals.db
```

**PostgreSQL**:
```
DATABASE_URL=postgresql://user:password@host:port/database
```

## Deployment

### Platform-Specific Instructions

**Heroku**:
1. Create `Procfile`: `web: gunicorn main:app`
2. Set environment variables in Heroku dashboard
3. Deploy via Git or GitHub integration

**Railway**:
1. Connect GitHub repository
2. Set environment variables in Railway dashboard
3. Deploy automatically on push

**Render**:
1. Connect GitHub repository
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `gunicorn main:app`

**DigitalOcean App Platform**:
1. Create app from GitHub repository
2. Configure environment variables
3. Set run command: `gunicorn --bind 0.0.0.0:$PORT main:app`

## API Endpoints

- `GET /api/hospital-data` - Current hospital data
- `GET /api/hospital-history/<code>?days=<n>` - Historical data for specific hospital
- `GET /api/scraping-status` - Last scraping status
- `GET /api/weather` - Current weather data
- `POST /api/manual-scrape` - Trigger manual data scraping

## Data Sources

- **Hospital Data**: [eHealth Saskatchewan Hospital Bed Capacity Report](https://www.ehealthsask.ca/reporting/Documents/SaskatoonHospitalBedCapacity.pdf)
- **Weather Data**: OpenWeatherMap API

## Hospital Codes

- `RUH`: Royal University Hospital
- `SPH`: St. Paul's Hospital
- `SCH`: Saskatoon City Hospital
- `JPCH`: Jim Pattison Children's Hospital

## Data Collection

The system automatically scrapes hospital data every hour using the APScheduler. Data is validated and filtered to remove anomalies before storage. The scraper handles:

- PDF table extraction using Camelot
- Data validation and anomaly detection
- Missing hospital handling (e.g., when SCH has 0 patients)
- Duplicate data filtering

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Disclaimer

This application is for informational purposes only. Hospital capacity data is extracted from publicly available eHealth Saskatchewan reports. For official medical information or emergencies, contact healthcare providers directly.