from flask import Flask
from extensions import db
from scheduler import start_scheduler
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///default.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the db with the app
db.init_app(app)

app.register_blueprint(main_routes)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        start_scheduler()
    app.run(debug=True)
else:
    # Ensure the app context is available for the scheduler in production
    with app.app_context():
        db.create_all()
        start_scheduler()
