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


@app.route('/api/error-report', methods=['POST'])
def submit_error_report():
    """Submit an error report"""
    try:
        data = request.get_json()
        
        if not data or not data.get('issue_type') or not data.get('description'):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Create new error report
        error_report = ErrorReport()
        error_report.issue_type = data['issue_type']
        error_report.description = data['description']
        error_report.contact_info = data.get('contact_info', '')
        
        db.session.add(error_report)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Error report submitted successfully',
            'report_id': error_report.id
        })
        
    except Exception as e:
        logging.error(f"Error submitting report: {str(e)}")
        return jsonify({'error': 'Failed to submit error report'}), 500


@app.route('/api/error-reports')
def get_error_reports():
    """Get all error reports (for admin use)"""
    try:
        reports = ErrorReport.query.order_by(ErrorReport.timestamp.desc()).limit(50).all()
        
        reports_data = []
        for report in reports:
            reports_data.append({
                'id': report.id,
                'issue_type': report.issue_type,
                'description': report.description,
                'contact_info': report.contact_info,
                'timestamp': report.timestamp.isoformat(),
                'status': report.status
            })
        
        return jsonify({
            'success': True,
            'reports': reports_data
        })
        
    except Exception as e:
        logging.error(f"Error fetching reports: {str(e)}")
        return jsonify({'error': 'Failed to fetch error reports'}), 500

@app.route('/admin')
def admin_dashboard():
    """Admin dashboard page"""
    return render_template('admin.html')

@app.route('/api/admin/scraping-logs')
def get_scraping_logs():
    """Get recent scraping logs for admin dashboard"""
    try:
        logs = ScrapingLog.query.order_by(ScrapingLog.timestamp.desc()).limit(50).all()
        return jsonify([{
            'id': log.id,
            'timestamp': log.timestamp.isoformat(),
            'status': log.status,
            'message': log.message,
            'pdf_url': log.pdf_url or ''
        } for log in logs])
    except Exception as e:
        logging.error(f"Error fetching scraping logs: {e}")
        return jsonify({'error': 'Failed to fetch scraping logs'}), 500

@app.route('/api/admin/stats')
def get_admin_stats():
    """Get system statistics for admin dashboard"""
    try:
        from datetime import datetime, timedelta
        
        # Get latest data timestamp
        latest_data = HospitalCapacity.query.order_by(HospitalCapacity.timestamp.desc()).first()
        last_update = latest_data.timestamp.strftime('%Y-%m-%d %H:%M') if latest_data else 'Never'
        
        # Count active data sources (hospitals with recent data)
        recent_threshold = datetime.utcnow() - timedelta(hours=6)
        active_hospitals = db.session.query(HospitalCapacity.hospital_code).filter(
            HospitalCapacity.timestamp >= recent_threshold
        ).distinct().count()
        
        # Count validation blocks (RUH rejections in logs)
        validation_blocks = ScrapingLog.query.filter(
            ScrapingLog.timestamp >= datetime.utcnow() - timedelta(hours=24),
            ScrapingLog.message.contains('RUH: No realistic patient count')
        ).count()
        
        # Calculate success rate
        total_attempts = ScrapingLog.query.filter(
            ScrapingLog.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        successful_attempts = ScrapingLog.query.filter(
            ScrapingLog.timestamp >= datetime.utcnow() - timedelta(hours=24),
            ScrapingLog.status == 'success'
        ).count()
        
        success_rate = round((successful_attempts / total_attempts * 100) if total_attempts > 0 else 100, 1)
        
        # Determine system status
        system_status = 'Active' if latest_data and latest_data.timestamp >= recent_threshold else 'Warning'
        
        return jsonify({
            'system_status': system_status,
            'active_sources': active_hospitals,
            'validation_blocks': validation_blocks,
            'success_rate': success_rate,
            'last_update': last_update
        })
    except Exception as e:
        logging.error(f"Error fetching admin stats: {e}")
        return jsonify({'error': 'Failed to fetch statistics'}), 500

@app.route('/api/admin/data-quality')
def get_data_quality():
    """Get data quality information for each hospital"""
    try:
        hospitals = ['RUH', 'SPH', 'SCH', 'JPCH']
        hospital_names = {
            'RUH': 'Royal University Hospital',
            'SPH': 'St. Paul\'s Hospital', 
            'SCH': 'Saskatoon City Hospital',
            'JPCH': 'Jim Pattison Children\'s Hospital'
        }
        
        quality_data = []
        for code in hospitals:
            latest = HospitalCapacity.query.filter_by(hospital_code=code).order_by(
                HospitalCapacity.timestamp.desc()
            ).first()
            
            if latest:
                # Determine data quality based on recency and validation
                hours_old = (datetime.utcnow() - latest.timestamp).total_seconds() / 3600
                
                if hours_old < 2:
                    quality = 'Good'
                elif hours_old < 6:
                    quality = 'Warning'
                else:
                    quality = 'Stale'
                
                # Special validation check for RUH
                if code == 'RUH' and latest.total_patients < 45:
                    quality = 'Invalid'
                
                quality_data.append({
                    'code': code,
                    'name': hospital_names[code],
                    'last_reading': latest.timestamp.strftime('%H:%M'),
                    'patient_count': latest.total_patients,
                    'quality': quality
                })
            else:
                quality_data.append({
                    'code': code,
                    'name': hospital_names[code],
                    'last_reading': 'No data',
                    'patient_count': 'N/A',
                    'quality': 'No Data'
                })
        
        return jsonify({'hospitals': quality_data})
    except Exception as e:
        logging.error(f"Error fetching data quality: {e}")
        return jsonify({'error': 'Failed to fetch data quality'}), 500

@app.route('/api/admin/error-reports/<int:report_id>', methods=['PATCH'])
def update_error_report_status(report_id):
    """Update error report status"""
    try:
        report = ErrorReport.query.get_or_404(report_id)
        data = request.get_json()
        
        if 'status' in data:
            report.status = data['status']
            db.session.commit()
            return jsonify({'success': True})
        
        return jsonify({'error': 'No status provided'}), 400
    except Exception as e:
        logging.error(f"Error updating error report: {e}")
        return jsonify({'error': 'Failed to update error report'}), 500

@app.route('/api/admin/trigger-scrape', methods=['POST'])
def trigger_manual_scrape():
    """Trigger manual data scraping"""
    try:
        from pdf_scraper import run_scraping
        result = run_scraping()
        
        if result:
            return jsonify({'success': True, 'message': 'Manual scrape completed successfully'})
        else:
            return jsonify({'success': False, 'message': 'Manual scrape failed'})
    except Exception as e:
        logging.error(f"Error triggering manual scrape: {e}")
        return jsonify({'error': 'Failed to trigger manual scrape'}), 500

@app.route('/api/admin/clear-old-data', methods=['POST'])
def clear_old_data():
    """Clear old hospital capacity data"""
    try:
        from datetime import datetime, timedelta
        
        # Delete data older than 30 days
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        old_records = HospitalCapacity.query.filter(HospitalCapacity.timestamp < cutoff_date)
        count = old_records.count()
        old_records.delete()
        
        # Also clear old scraping logs
        old_logs = ScrapingLog.query.filter(ScrapingLog.timestamp < cutoff_date)
        log_count = old_logs.count()
        old_logs.delete()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f'Cleared {count} old capacity records and {log_count} old log entries'
        })
    except Exception as e:
        logging.error(f"Error clearing old data: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to clear old data'}), 500
