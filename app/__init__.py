# app/__init__.py

from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from config import Config
# DO NOT import models here

db = SQLAlchemy() # Define db early
migrate = Migrate()
bcrypt = Bcrypt()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app) # Initialize db with app
    migrate.init_app(app, db)
    bcrypt.init_app(app)

    # Import models HERE, after db is initialized
    from app import models 
    # Or be more specific if needed later: from .models import ChatSession 

    # --- Register Blueprints ---
    from .auth.routes import auth_bp
    app.register_blueprint(auth_bp)
    from .patient.routes import patient_bp
    app.register_blueprint(patient_bp)
    from .doctor.routes import doctor_bp
    app.register_blueprint(doctor_bp)
    from .main.routes import main_bp
    app.register_blueprint(main_bp)

    # --- Context Processor ---
    @app.context_processor
    def inject_chat_sessions():
        # Import ChatSession here or rely on the 'models' import above
        from .models import ChatSession 
        chat_sessions_data = None 
        if 'user_id' in session and session.get('user_type') == 'patient':
            try:
                chat_sessions_data = ChatSession.query.filter_by(patient_id=session['user_id']).order_by(ChatSession.start_time.desc()).all()
            except Exception as e:
                print(f"Error fetching chat sessions: {e}") 
                chat_sessions_data = [] 
        return dict(chat_sessions=chat_sessions_data) 

    return app