from datetime import datetime
from app import db

class HospitalCapacity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_code = db.Column(db.String(10), nullable=False)
    hospital_name = db.Column(db.String(100), nullable=False)
    total_patients = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<HospitalCapacity {self.hospital_code}: {self.total_patients} patients>'

class ScrapingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<ScrapingLog {self.timestamp}: {self.status}>'