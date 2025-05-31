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
    """Get latest hospital capacity data"""
    try:
        # Get latest data for each hospital
        hospitals = []
        for code in ['RUH', 'SPH', 'SCH', 'JPCH']:
            latest = HospitalCapacity.query.filter_by(hospital_code=code).order_by(
                HospitalCapacity.timestamp.desc()
            ).first()
            
            if latest:
                hospitals.append({
                    'hospital_code': latest.hospital_code,
                    'hospital_name': latest.hospital_name,
                    'total_patients': latest.total_patients,
                    'timestamp': latest.timestamp.isoformat()
                })
        
        return jsonify({
            'success': True,
            'data': hospitals
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/hospital-history/<hospital_code>')
def get_hospital_history(hospital_code):
    """Get historical data for a specific hospital"""
    try:
        # Get last 24 hours of data
        since = datetime.utcnow() - timedelta(hours=24)
        
        records = HospitalCapacity.query.filter(
            HospitalCapacity.hospital_code == hospital_code,
            HospitalCapacity.timestamp >= since
        ).order_by(HospitalCapacity.timestamp.desc()).limit(50).all()
        
        data = []
        for record in records:
            data.append({
                'hospital_code': record.hospital_code,
                'total_patients': record.total_patients,
                'timestamp': record.timestamp.isoformat()
            })
        
        return jsonify({
            'success': True,
            'hospital_code': hospital_code,
            'data': data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/scraping-status')
def get_scraping_status():
    """Get the latest scraping status"""
    try:
        latest_log = ScrapingLog.query.order_by(ScrapingLog.timestamp.desc()).first()
        
        if latest_log:
            return jsonify({
                'success': True,
                'status': latest_log.status,
                'message': latest_log.message,
                'timestamp': latest_log.timestamp.isoformat(),
                'hospitals_processed': latest_log.hospitals_processed
            })
        else:
            return jsonify({
                'success': True,
                'status': 'no_data',
                'message': 'No scraping logs available',
                'timestamp': None,
                'hospitals_processed': 0
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500