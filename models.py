from datetime import datetime
from app import db

class HospitalCapacity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_code = db.Column(db.String(10), nullable=False)  # RUH, SPH, SCH
    hospital_name = db.Column(db.String(100), nullable=False)
    occupied_beds = db.Column(db.Integer)
    total_beds = db.Column(db.Integer)
    capacity_percentage = db.Column(db.Float)
    admitted_pts_in_ed = db.Column(db.Integer)
    active_patients = db.Column(db.Integer)
    consults = db.Column(db.Integer)
    total_patients = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<HospitalCapacity {self.hospital_code}: {self.occupied_beds}/{self.total_beds}>'

class ScrapingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False)  # success, error
    message = db.Column(db.Text)
    pdf_url = db.Column(db.String(500))
    
    def __repr__(self):
        return f'<ScrapingLog {self.timestamp}: {self.status}>'
