import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-key")

# Database configuration
#app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
#app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
  #  "pool_recycle": 300,
   # "pool_pre_ping": True,
#}
import os
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///hospitals.db')

# Initialize database
db.init_app(app)

with app.app_context():
    from models import HospitalCapacity, ScrapingLog
    db.create_all()