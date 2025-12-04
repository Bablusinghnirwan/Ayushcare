from flask import render_template, redirect, url_for, request, session, flash, current_app
from app.models import Patient, MedicalRecord, PatientCondition, ChatHistory, ChatSession
from app import db
from functools import wraps
from flask import Blueprint
from werkzeug.utils import secure_filename
import os
from flask import session

# THEN, you CREATE the blueprint variable
patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

def patient_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'patient':
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@patient_bp.route('/dashboard/')
@patient_login_required
def dashboard():
    patient = Patient.query.get(session['user_id'])

    # Current chat session ko manage karein
    current_session_id = session.get('current_chat_session_id')
    current_session = None
    if current_session_id:
        current_session = ChatSession.query.get(current_session_id)
        # Ensure the session belongs to the current patient
        if current_session and current_session.patient_id != patient.id:
             current_session = None 
             session.pop('current_chat_session_id', None) # Remove invalid session id

    # Agar koi valid current session nahi hai, toh naya banayein
    if not current_session:
        new_session = ChatSession(patient_id=patient.id, title="New Chat") 
        db.session.add(new_session)
        db.session.commit()
        session['current_chat_session_id'] = new_session.id
        current_session_id = new_session.id

    # Sidebar ke liye saare sessions fetch karein (naye sabse upar)
    chat_sessions = ChatSession.query.filter_by(patient_id=patient.id).order_by(ChatSession.start_time.desc()).all()

    # Current session ke messages fetch karein (purane sabse upar)
    current_chat_messages = ChatHistory.query.filter_by(session_id=current_session_id).order_by(ChatHistory.timestamp.asc()).all()

    # Baaki ka data (records, conditions) waise hi fetch karein
    medical_records = MedicalRecord.query.filter_by(patient_id=patient.id).order_by(MedicalRecord.record_date.desc()).all()
    patient_conditions = PatientCondition.query.filter_by(patient_id=patient.id, end_date=None).order_by(PatientCondition.start_date.desc()).all()

    return render_template(
        'patient_dashboard.html', 
        patient=patient, 
        records=medical_records, 
        conditions=patient_conditions,
        chat_sessions=chat_sessions, # Sidebar ke liye
        current_chat_messages=current_chat_messages # Chat window ke liye
    )

@patient_bp.route('/chat/new')
@patient_login_required
def new_chat():
    # Clear the current session ID from Flask session
    session.pop('current_chat_session_id', None)
    # Redirect back to the dashboard, which will create a new session
    return redirect(url_for('patient.dashboard'))

@patient_bp.route('/chat/load/<int:session_id>')
@patient_login_required
def load_chat(session_id):
    # Verify the session belongs to the current patient
    chat_session_to_load = ChatSession.query.filter_by(id=session_id, patient_id=session['user_id']).first()
    if chat_session_to_load:
        # Set the clicked session ID as the current one in Flask session
        session['current_chat_session_id'] = session_id
    else:
        flash('Invalid chat session selected.', 'warning')
    # Redirect back to the dashboard to load the messages for this session
    return redirect(url_for('patient.dashboard'))

@patient_bp.route('/onboarding/<int:step>/', methods=['GET', 'POST'])
@patient_login_required
def onboarding(step):
    patient = Patient.query.get(session['user_id'])
    
    if request.method == 'POST':
        if 'onboarding_data' not in session:
            session['onboarding_data'] = {}
            
        if step == 1:
            session['onboarding_data']['blood_group'] = request.form.get('blood_group')
            session['onboarding_data']['height'] = request.form.get('height')
            session['onboarding_data']['weight'] = request.form.get('weight')
            session.modified = True
            return redirect(url_for('patient.onboarding', step=2))
        
        elif step == 2:
            data = session['onboarding_data']
            data['allergies'] = request.form.get('allergies')
            data['chronic_diseases'] = request.form.get('chronic_diseases')
            
            patient.blood_group = data.get('blood_group')
            patient.height = data.get('height')
            patient.weight = data.get('weight')
            patient.allergies = data.get('allergies')
            patient.chronic_diseases = data.get('chronic_diseases')
            patient.onboarding_complete = True
            db.session.commit()
            
            session.pop('onboarding_data', None)
            flash('Your profile is complete!', 'success')
            return redirect(url_for('patient.profile'))

    return render_template('patient_onboarding.html', step=step)

@patient_bp.route('/profile/')
@patient_login_required
def profile():
    patient = Patient.query.get(session['user_id'])
    return render_template('patient_profile.html', patient=patient)

@patient_bp.route('/profile/edit/', methods=['GET', 'POST'])
@patient_login_required
def edit_profile():
    patient = Patient.query.get(session['user_id'])
    
    if request.method == 'POST':
        # Form se data update karein
        patient.name = request.form.get('name')
        
        # --- YAHAN PAR DATE KA FIX HAI ---
        dob = request.form.get('date_of_birth')
        patient.date_of_birth = dob if dob else None # Agar date khaali hai, toh None save karein

        patient.blood_group = request.form.get('blood_group')
        patient.height = request.form.get('height') or None
        patient.weight = request.form.get('weight') or None
        patient.allergies = request.form.get('allergies')
        patient.chronic_diseases = request.form.get('chronic_diseases')
        
        # --- YAHAN FILE UPLOAD KA SAHI LOGIC HAI ---
        profile_pic = request.files.get('profile_picture')
        if profile_pic and profile_pic.filename != '':
            filename = secure_filename(profile_pic.filename)
            # File ko 'app/static/uploads/patient_dps/' folder me save karein
            upload_folder = os.path.join(current_app.root_path, 'static/uploads/patient_dps')
            os.makedirs(upload_folder, exist_ok=True) # Agar folder na ho toh banayein
            profile_pic.save(os.path.join(upload_folder, filename))
            # Database me sirf file ka naam save karein
            patient.profile_picture = filename
            
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('patient.profile'))
        
    return render_template('edit_patient_profile.html', patient=patient)