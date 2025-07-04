from extensions import db

class Hospital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    data = db.relationship('HospitalData', backref='hospital', lazy=True)

class HospitalData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    inpatient_beds = db.Column(db.Integer)
    overcapacity_beds = db.Column(db.Integer)
    total_patients = db.Column(db.Integer)
    waiting_for_inpatient_bed = db.Column(db.Integer)

class ScrapingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=True)
