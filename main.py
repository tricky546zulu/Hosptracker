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
        db.create_all()

    @app.route('/')
    def index():
        return render_template('index.html')

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
