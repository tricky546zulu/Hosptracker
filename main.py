from flask import Flask
from models import db
from routes import main_routes
from scheduler import start_scheduler
import os

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///default.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(main_routes)

    # It's important to create tables within the app context
    with app.app_context():
        db.create_all()
        # Start the scheduler only once when the app is initialized
        start_scheduler()

    return app

app = create_app()

if __name__ == "__main__":
    # This block is for local development
    app.run(debug=True)
