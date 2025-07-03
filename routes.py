from flask import Blueprint, jsonify, request
from models import db, HospitalData, ScrapingLog
import requests
from datetime import datetime, timedelta
import os # Import os to access environment variables

main_routes = Blueprint('main_routes', __name__)

@main_routes.route('/')
def index():
    # This can be your main HTML page
    return "Welcome to Hosptracker!"

@main_routes.route('/api/hospital-data', methods=['GET'])
def get_hospital_data():
    latest_data = db.session.query(
        HospitalData.hospital_code,
        db.func.max(HospitalData.timestamp).label('max_timestamp')
    ).group_by(HospitalData.hospital_code).subquery()

    results = db.session.query(HospitalData).join(
        latest_data,
        db.and_(
            HospitalData.hospital_code == latest_data.c.hospital_code,
            HospitalData.timestamp == latest_data.c.max_timestamp
        )
    ).all()

    return jsonify([
        {
            "hospital_code": r.hospital_code,
            "patient_count": r.patient_count,
            "timestamp": r.timestamp.isoformat()
        } for r in results
    ])

@main_routes.route('/api/scraping-status', methods=['GET'])
def get_scraping_status():
    latest_log = ScrapingLog.query.order_by(ScrapingLog.timestamp.desc()).first()
    if latest_log:
        return jsonify({
            "status": latest_log.status,
            "message": latest_log.message,
            "timestamp": latest_log.timestamp.isoformat()
        })
    return jsonify({"status": "N/A", "message": "No scraping logs found."})

@main_routes.route('/api/weather', methods=['GET'])
def get_weather():
    # IMPORTANT: You must set the WEATHER_API_KEY environment variable on Render
    api_key = os.environ.get('WEATHER_API_KEY')
    if not api_key:
        return jsonify({"error": "Weather API key is not configured"}), 500

    city = "Saskatoon"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@main_routes.route('/api/hospital-history/<string:hospital_code>', methods=['GET'])
def get_hospital_history(hospital_code):
    days_str = request.args.get('days', '7')
    try:
        days = int(days_str)
    except ValueError:
        return jsonify({"error": "Invalid 'days' parameter. Must be an integer."}), 400

    time_delta = datetime.utcnow() - timedelta(days=days)

    history = HospitalData.query.filter(
        HospitalData.hospital_code == hospital_code.upper(),
        HospitalData.timestamp >= time_delta
    ).order_by(HospitalData.timestamp.asc()).all()

    return jsonify([
        {
            "patient_count": h.patient_count,
            "timestamp": h.timestamp.isoformat()
        } for h in history
    ])
