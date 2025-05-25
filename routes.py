import logging
from flask import render_template, jsonify
from datetime import datetime, timedelta
from app import app, db
from models import HospitalCapacity, ScrapingLog

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/hospital-data')
def get_hospital_data():
    """API endpoint to get latest hospital capacity data"""
    try:
        # Get the latest data for each hospital
        hospitals = ['RUH', 'SPH', 'SCH']
        hospital_data = {}
        
        for hospital in hospitals:
            latest = HospitalCapacity.query.filter_by(hospital_code=hospital)\
                .order_by(HospitalCapacity.timestamp.desc()).first()
            
            if latest:
                hospital_data[hospital] = {
                    'hospital_name': latest.hospital_name,
                    'occupied_beds': latest.occupied_beds or 0,
                    'total_beds': latest.total_beds or 0,
                    'capacity_percentage': latest.capacity_percentage or 0,
                    'admitted_pts_in_ed': latest.admitted_pts_in_ed or 0,
                    'timestamp': latest.timestamp.isoformat() if latest.timestamp else None,
                    'status': 'success'
                }
            else:
                hospital_data[hospital] = {
                    'hospital_name': get_hospital_name(hospital),
                    'occupied_beds': 0,
                    'total_beds': 0,
                    'capacity_percentage': 0,
                    'admitted_pts_in_ed': 0,
                    'timestamp': None,
                    'status': 'no_data'
                }
        
        return jsonify({
            'status': 'success',
            'data': hospital_data,
            'last_updated': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error getting hospital data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve hospital data',
            'data': {}
        }), 500

@app.route('/api/hospital-history/<hospital_code>')
def get_hospital_history(hospital_code):
    """Get historical data for a specific hospital"""
    try:
        # Get data from the last 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        history = HospitalCapacity.query.filter(
            HospitalCapacity.hospital_code == hospital_code.upper(),
            HospitalCapacity.timestamp >= cutoff_time
        ).order_by(HospitalCapacity.timestamp.asc()).all()
        
        history_data = []
        for record in history:
            history_data.append({
                'timestamp': record.timestamp.isoformat(),
                'occupied_beds': record.occupied_beds or 0,
                'total_beds': record.total_beds or 0,
                'capacity_percentage': record.capacity_percentage or 0,
                'admitted_pts_in_ed': record.admitted_pts_in_ed or 0
            })
        
        return jsonify({
            'status': 'success',
            'hospital_code': hospital_code.upper(),
            'hospital_name': get_hospital_name(hospital_code.upper()),
            'data': history_data
        })
        
    except Exception as e:
        logging.error(f"Error getting hospital history for {hospital_code}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to retrieve history for {hospital_code}'
        }), 500

@app.route('/api/scraping-status')
def get_scraping_status():
    """Get the latest scraping status"""
    try:
        latest_log = ScrapingLog.query.order_by(ScrapingLog.timestamp.desc()).first()
        
        if latest_log:
            return jsonify({
                'status': 'success',
                'last_scrape': {
                    'timestamp': latest_log.timestamp.isoformat(),
                    'status': latest_log.status,
                    'message': latest_log.message
                }
            })
        else:
            return jsonify({
                'status': 'success',
                'last_scrape': {
                    'timestamp': None,
                    'status': 'never_run',
                    'message': 'Scraping has not run yet'
                }
            })
            
    except Exception as e:
        logging.error(f"Error getting scraping status: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to retrieve scraping status'
        }), 500

def get_hospital_name(code):
    """Get full hospital name from code"""
    hospital_names = {
        'RUH': 'Royal University Hospital',
        'SPH': "St. Paul's Hospital", 
        'SCH': 'Saskatoon City Hospital'
    }
    return hospital_names.get(code, code)
