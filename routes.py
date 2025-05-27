import logging
from flask import render_template, jsonify, request
from datetime import datetime, timedelta
from app import app, db
from models import HospitalCapacity, ScrapingLog, ErrorReport
from sqlalchemy import func, extract

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/hospital-data')
def get_hospital_data():
    """API endpoint to get latest hospital capacity data"""
    try:
        # Get the latest data for each hospital
        hospitals = ['RUH', 'SPH', 'SCH', 'JPCH']
        hospital_data = {}
        
        for hospital in hospitals:
            latest = HospitalCapacity.query.filter_by(hospital_code=hospital)\
                .order_by(HospitalCapacity.timestamp.desc()).first()
            
            if latest:
                hospital_data[hospital] = {
                    'hospital_name': latest.hospital_name,
                    'total_patients': latest.total_patients or 0,
                    'timestamp': latest.timestamp.isoformat() if latest.timestamp else None,
                    'status': 'success'
                }
            else:
                hospital_data[hospital] = {
                    'hospital_name': get_hospital_name(hospital),
                    'total_patients': 0,
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
                'total_patients': record.total_patients or 0
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
        'SCH': 'Saskatoon City Hospital',
        'JPCH': 'Jim Pattison Children\'s Hospital'
    }
    return hospital_names.get(code, code)

@app.route('/api/analytics/<int:days>')
def get_analytics_data(days):
    """Get analytics data for specified number of days"""
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get data within date range
        hospital_data = db.session.query(HospitalCapacity).filter(
            HospitalCapacity.timestamp >= start_date,
            HospitalCapacity.timestamp <= end_date,
            HospitalCapacity.hospital_code.in_(['RUH', 'SPH', 'SCH'])
        ).order_by(HospitalCapacity.timestamp).all()
        
        if not hospital_data:
            return jsonify({
                'status': 'success',
                'summary': {
                    'total_data_points': 0,
                    'avg_patients_per_day': 0,
                    'peak_patient_count': 0,
                    'busiest_hospital': '-'
                },
                'hospital_data': {},
                'comparison': {'averages': {}, 'peaks': {}}
            })
        
        # Calculate summary statistics
        total_points = len(hospital_data)
        valid_patients = [h.total_patients for h in hospital_data if h.total_patients is not None]
        
        # Calculate total average patients per day across all hospitals combined
        if valid_patients and days > 0:
            # Group by date and sum all hospitals for each day
            daily_totals = {}
            for h in hospital_data:
                if h.total_patients is not None:
                    date_key = h.timestamp.date()
                    if date_key not in daily_totals:
                        daily_totals[date_key] = {}
                    daily_totals[date_key][h.hospital_code] = h.total_patients
            
            # Calculate daily sums (all hospitals combined per day)
            daily_sums = []
            for date, hospitals in daily_totals.items():
                # Get the latest reading for each hospital on each day
                daily_sum = sum(hospitals.values())
                daily_sums.append(daily_sum)
            
            avg_per_day = sum(daily_sums) / len(daily_sums) if daily_sums else 0
        else:
            avg_per_day = 0
            
        peak_count = max(valid_patients) if valid_patients else 0
        
        # Find busiest hospital
        hospital_totals = {}
        for hospital in hospital_data:
            code = hospital.hospital_code
            if code not in hospital_totals:
                hospital_totals[code] = []
            if hospital.total_patients is not None:
                hospital_totals[code].append(hospital.total_patients)
        
        hospital_averages = {code: sum(values)/len(values) if values else 0 
                           for code, values in hospital_totals.items()}
        busiest_hospital = '-'
        if hospital_averages:
            max_avg = 0
            for code, avg in hospital_averages.items():
                if avg > max_avg:
                    max_avg = avg
                    busiest_hospital = code
        
        # Generate hospital-specific analytics
        analytics_data = {}
        comparison_data = {'averages': {}, 'peaks': {}}
        
        for hospital_code in ['RUH', 'SPH', 'SCH']:
            hospital_records = [h for h in hospital_data if h.hospital_code == hospital_code]
            
            if hospital_records:
                # Daily trends
                daily_trends = calculate_daily_trends(hospital_records, start_date, days)
                
                # Hourly patterns
                hourly_patterns = calculate_hourly_patterns(hospital_records)
                
                # Weekly patterns
                weekly_patterns = calculate_weekly_patterns(hospital_records)
                
                analytics_data[hospital_code] = {
                    'daily_trends': daily_trends,
                    'hourly_patterns': hourly_patterns,
                    'weekly_patterns': weekly_patterns
                }
                
                # Comparison data - use latest authentic values instead of averages
                patient_counts = [h.total_patients for h in hospital_records if h.total_patients is not None]
                if patient_counts:
                    # Use the most recent authentic value for current comparison
                    latest_value = hospital_records[0].total_patients if hospital_records else 0
                    comparison_data['averages'][hospital_code] = latest_value
                    comparison_data['peaks'][hospital_code] = {
                        'average': latest_value,
                        'peak': max(patient_counts)
                    }
        
        return jsonify({
            'status': 'success',
            'summary': {
                'total_data_points': total_points,
                'avg_patients_per_day': round(avg_per_day, 1),
                'peak_patient_count': peak_count,
                'busiest_hospital': busiest_hospital
            },
            'hospital_data': analytics_data,
            'comparison': comparison_data
        })
        
    except Exception as e:
        logging.error(f"Error generating analytics: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def calculate_daily_trends(hospital_records, start_date, days):
    """Calculate daily trend data"""
    daily_data = {}
    
    for record in hospital_records:
        if record.total_patients is not None:
            date_key = record.timestamp.date()
            if date_key not in daily_data:
                daily_data[date_key] = []
            daily_data[date_key].append(record.total_patients)
    
    # Generate daily averages
    daily_trends = []
    for i in range(days):
        current_date = (start_date + timedelta(days=i)).date()
        if current_date in daily_data:
            avg_patients = sum(daily_data[current_date]) / len(daily_data[current_date])
        else:
            avg_patients = 0
        
        daily_trends.append({
            'date': current_date.isoformat(),
            'avg_patients': round(avg_patients, 1)
        })
    
    return daily_trends

def calculate_hourly_patterns(hospital_records):
    """Calculate hourly pattern data"""
    hourly_data = {}
    
    for record in hospital_records:
        if record.total_patients is not None:
            hour = record.timestamp.hour
            if hour not in hourly_data:
                hourly_data[hour] = []
            hourly_data[hour].append(record.total_patients)
    
    # Generate hourly averages
    hourly_patterns = []
    for hour in range(24):
        if hour in hourly_data:
            avg_patients = sum(hourly_data[hour]) / len(hourly_data[hour])
        else:
            avg_patients = 0
        
        hourly_patterns.append({
            'hour': hour,
            'avg_patients': round(avg_patients, 1)
        })
    
    return hourly_patterns

def calculate_weekly_patterns(hospital_records):
    """Calculate weekly pattern data (day of week)"""
    weekly_data = {}
    
    for record in hospital_records:
        if record.total_patients is not None:
            day_of_week = record.timestamp.weekday()  # 0=Monday, 6=Sunday
            # Convert to 0=Sunday, 6=Saturday for consistency
            day_of_week = (day_of_week + 1) % 7
            
            if day_of_week not in weekly_data:
                weekly_data[day_of_week] = []
            weekly_data[day_of_week].append(record.total_patients)
    
    # Generate weekly averages
    weekly_patterns = []
    for day in range(7):  # 0=Sunday through 6=Saturday
        if day in weekly_data:
            avg_patients = sum(weekly_data[day]) / len(weekly_data[day])
        else:
            avg_patients = 0
        
        weekly_patterns.append({
            'day_of_week': day,
            'avg_patients': round(avg_patients, 1)
        })
    
    return weekly_patterns
