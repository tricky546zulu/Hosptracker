from flask import render_template, jsonify, request
from datetime import datetime, timedelta
import requests
import os
from app import app, db
from models import HospitalCapacity, ScrapingLog

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/history')
def history():
    """Historical data page"""
    return render_template('history.html')

@app.route('/clinics')
def clinics():
    """Medical clinics page"""
    return render_template('clinics.html')

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
                    'admitted_patients_in_ed': latest.admitted_patients_in_ed,
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
        # Get days parameter, default to 1 day (24 hours)
        days = request.args.get('days', 1, type=int)
        since = datetime.utcnow() - timedelta(days=days)
        
        records = HospitalCapacity.query.filter(
            HospitalCapacity.hospital_code == hospital_code,
            HospitalCapacity.timestamp >= since
        ).order_by(HospitalCapacity.timestamp.desc()).all()
        
        data = []
        for record in records:
            data.append({
                'hospital_code': record.hospital_code,
                'total_patients': record.total_patients,
                'admitted_patients_in_ed': record.admitted_patients_in_ed,
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
                'timestamp': latest_log.timestamp.isoformat()
            })
        else:
            return jsonify({
                'success': True,
                'status': 'no_data',
                'message': 'No scraping logs available',
                'timestamp': None
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/weather')
def get_weather():
    """Get current weather for Saskatoon"""
    try:
        api_key = os.environ.get('OPENWEATHERMAP_API_KEY')
        if not api_key:
            return jsonify({'error': 'Weather API key not configured'}), 500
            
        # Saskatoon coordinates
        lat = 52.1332
        lon = -106.6700
        
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        weather_data = response.json()
        
        return jsonify({
            'success': True,
            'data': {
                'temperature': round(weather_data['main']['temp']),
                'feels_like': round(weather_data['main']['feels_like']),
                'humidity': weather_data['main']['humidity'],
                'description': weather_data['weather'][0]['description'].title(),
                'icon': weather_data['weather'][0]['icon'],
                'wind_speed': round(weather_data['wind']['speed'] * 3.6, 1),  # Convert m/s to km/h
                'visibility': weather_data.get('visibility', 0) / 1000,  # Convert to km
                'pressure': weather_data['main']['pressure'],
                'city': weather_data['name']
            }
        })
        
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Weather service unavailable: {str(e)}'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/manual-scrape', methods=['POST'])
def manual_scrape():
    """Manually trigger hospital data scraping"""
    try:
        from pdf_scraper import run_scraping
        success = run_scraping()
        if success:
            return jsonify({'success': True, 'message': 'Manual scraping completed'})
        else:
            return jsonify({'success': False, 'message': 'Scraping failed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/medical-clinics')
def get_medical_clinics():
    """Get medical clinics in Saskatoon using Google Places API"""
    try:
        api_key = os.environ.get('GOOGLE_PLACES_API_KEY')
        if not api_key:
            return jsonify({
                'success': False, 
                'error': 'Google Places API key not configured',
                'clinics': []
            })
        
        # Saskatoon coordinates
        location = "52.1332,-106.6700"  # Saskatoon center
        radius = 25000  # 25km radius
        
        # Search for medical clinics
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            'location': location,
            'radius': radius,
            'type': 'doctor',
            'keyword': 'clinic walk-in medical',
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            clinics = []
            
            for place in data.get('results', []):
                # Get detailed information for each clinic
                clinic_details = get_clinic_details(place['place_id'], api_key)
                
                clinic = {
                    'name': place.get('name', 'Unknown Clinic'),
                    'address': place.get('vicinity', ''),
                    'rating': place.get('rating'),
                    'isOpen': is_clinic_open(place.get('opening_hours', {})),
                    'phone': clinic_details.get('phone'),
                    'website': clinic_details.get('website'),
                    'hours': clinic_details.get('hours'),
                    'directions': f"https://www.google.com/maps/place/?q=place_id:{place['place_id']}"
                }
                clinics.append(clinic)
            
            # Sort by open status first, then by rating
            clinics.sort(key=lambda x: (not x['isOpen'], -(x['rating'] or 0)))
            
            return jsonify({
                'success': True,
                'clinics': clinics[:20]  # Limit to 20 results
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Google Places API request failed',
                'clinics': []
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'clinics': []
        })

def get_clinic_details(place_id, api_key):
    """Get detailed information for a specific clinic"""
    try:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            'place_id': place_id,
            'fields': 'formatted_phone_number,website,opening_hours',
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            result = data.get('result', {})
            
            hours = None
            if 'opening_hours' in result and 'weekday_text' in result['opening_hours']:
                # Get today's hours
                import datetime
                today_idx = datetime.datetime.now().weekday()
                if today_idx < len(result['opening_hours']['weekday_text']):
                    hours = result['opening_hours']['weekday_text'][today_idx]
            
            return {
                'phone': result.get('formatted_phone_number'),
                'website': result.get('website'),
                'hours': hours
            }
    except:
        pass
    
    return {}

def is_clinic_open(opening_hours):
    """Determine if clinic is currently open"""
    if not opening_hours:
        return None
    
    return opening_hours.get('open_now', None)