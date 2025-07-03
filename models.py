from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class HospitalData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_code = db.Column(db.String(10), nullable=False)
    patient_count = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ScrapingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=True)
