from flask import Flask, jsonify, render_template, request
from extensions import db
import os
import requests

def create_app():
    """Creates and configures a Flask application."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///hospitals.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        from models import Hospital, HospitalData
        db.create_all()

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/history')
    def history():
        return render_template('history.html')

    @app.route('/api/hospital-data')
    def get_hospital_data():
        from models import Hospital, HospitalData
        hospitals = Hospital.query.all()
        data = []
        for hospital in hospitals:
            latest_data = HospitalData.query.filter_by(hospital_id=hospital.id).order_by(HospitalData.timestamp.desc()).first()
            if latest_data:
                data.append({
                    'code': hospital.code,
                    'name': hospital.name,
                    'timestamp': latest_data.timestamp.isoformat(),
                    'inpatient_beds': latest_data.inpatient_beds,
                    'overcapacity_beds': latest_data.overcapacity_beds,
                    'total_patients': latest_data.total_patients,
                    'waiting_for_inpatient_bed': latest_data.waiting_for_inpatient_bed
                })
        return jsonify(data)

    @app.route('/api/hospital-history/<hospital_code>')
    def get_hospital_history(hospital_code):
        from models import Hospital, HospitalData
        days = request.args.get('days', 7, type=int)
        from datetime import datetime, timedelta
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        hospital = Hospital.query.filter_by(code=hospital_code).first()
        if not hospital:
            return jsonify({"error": "Hospital not found"}), 404

        history_data = HospitalData.query.filter(
            HospitalData.hospital_id == hospital.id,
            HospitalData.timestamp >= start_date
        ).order_by(HospitalData.timestamp.asc()).all()

        return jsonify([{
            'timestamp': d.timestamp.isoformat(),
            'total_patients': d.total_patients,
            'waiting_for_inpatient_bed': d.waiting_for_inpatient_bed
        } for d in history_data])

    @app.route('/api/weather')
    def get_weather():
        api_key = os.environ.get('WEATHER_API_KEY')
        if not api_key:
            return jsonify({"error": "Weather API key not configured"}), 500

        lat = 52.1332
        lon = -106.6700
        url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"

        try:
            response = requests.get(url)
            response.raise_for_status()
            return jsonify(response.json())
        except requests.exceptions.RequestException as e:
            return jsonify({"error": str(e)}), 500

    return app

app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
