from flask import render_template, redirect, url_for, request, session, flash, current_app
from app.models import Doctor, Patient, MedicalRecord, PatientCondition, Appointment
from app import db
from functools import wraps
from flask import Blueprint
from werkzeug.utils import secure_filename
import os
# THEN, you CREATE the blueprint variable
doctor_bp = Blueprint('doctor', __name__, url_prefix='/doctor')

# Decorator to check if doctor is logged in
def doctor_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'doctor':
            flash('Please log in as a doctor to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# app/doctor/routes.py me dashboard function ko isse replace karein

@doctor_bp.route('/dashboard/', methods=['GET', 'POST'])
@doctor_login_required
def dashboard():
    doctor = Doctor.query.get(session['user_id'])

    if request.method == 'POST':
        patient_id = request.form.get('patient')
        patient = Patient.query.get(patient_id)
        if patient:
            # --- YAHAN NAYA FILE UPLOAD LOGIC HAI ---
            report_file = request.files.get('report_file')
            filename = None
            if report_file and report_file.filename != '':
                filename = secure_filename(report_file.filename)
                # File ko 'app/static/health_reports/' folder me save karein
                upload_folder = os.path.join(current_app.root_path, 'static/health_reports')
                os.makedirs(upload_folder, exist_ok=True) # Agar folder na ho toh banayein
                report_file.save(os.path.join(upload_folder, filename))

            new_record = MedicalRecord(
                doctor_id=doctor.id,
                patient_id=patient.id,
                symptoms=request.form.get('symptoms'),
                diagnosis=request.form.get('diagnosis'),
                prescription=request.form.get('prescription'),
                dose=request.form.get('dose'),
                report_file=filename  # Database me file ka naam save karein
            )
            db.session.add(new_record)
            db.session.commit()
            flash('Medical record added successfully!', 'success')
        return redirect(url_for('doctor.dashboard'))

    # GET request ka logic waise hi rahega
    # ... (baaki ka GET logic) ...
    all_patients = Patient.query.all()
    records_by_doctor = MedicalRecord.query.filter_by(doctor_id=doctor.id).order_by(MedicalRecord.record_date.desc()).all()
    active_conditions = PatientCondition.query.filter(PatientCondition.end_date.is_(None)).all()
    doctor_appointments = Appointment.query.filter_by(doctor_id=doctor.id).order_by(Appointment.appointment_datetime).all()
    context = {
        'doctor': doctor,
        'patients': all_patients,
        'records': records_by_doctor,
        'active_conditions': active_conditions,
        'appointments': doctor_appointments,
    }
    return render_template('doctor_dashboard.html', **context)


@doctor_bp.route('/appointments/')
@doctor_login_required
def appointments():
    doctor = Doctor.query.get(session['user_id'])
    all_appointments = Appointment.query.filter_by(doctor_id=doctor.id).order_by(Appointment.appointment_datetime.desc()).all()
    return render_template('doctor_appointments.html', doctor=doctor, appointments=all_appointments)

@doctor_bp.route('/appointments/update/<int:appointment_id>/', methods=['POST'])
@doctor_login_required
def update_appointment_status(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.doctor.id == session['user_id']:
        new_status = request.form.get('status')
        # Simple string comparison is enough here as we used Enum in model
        appointment.status = new_status
        db.session.commit()
        flash('Appointment status updated.', 'success')
    else:
        flash('You are not authorized to update this appointment.', 'danger')
    return redirect(url_for('doctor.appointments'))

@doctor_bp.route('/search/', methods=['GET', 'POST'])
@doctor_login_required
def search_patient():
    doctor = Doctor.query.get(session['user_id'])
    context = {}

    # POST LOGIC (Jab Aadhar search kiya jaata hai)
    if request.method == 'POST':
        aadhar_query = request.form.get('aadhar_number', '').strip()
        if aadhar_query:
            patient = Patient.query.filter_by(aadhar_number=aadhar_query).first()
            if patient:
                records = MedicalRecord.query.filter_by(patient_id=patient.id).order_by(MedicalRecord.record_date.desc()).all()
                context = {
                    'patient_found': True,
                    'patient': patient,
                    'records': records,
                    'search_query': aadhar_query
                }
            else:
                flash(f"'{aadhar_query}' Aadhar number waala koi patient nahi mila.", 'warning')
                context['search_query'] = aadhar_query
    
    # GET LOGIC (Yeh hamesha chalega, page load hone par bhi)
    # Hamesha doctor ki apni history fetch karo aur template ko bhejo
    records_by_doctor = MedicalRecord.query.filter_by(doctor_id=doctor.id).order_by(MedicalRecord.record_date.desc()).all()
    context['records_by_doctor'] = records_by_doctor

    return render_template('search_patient.html', **context)


@doctor_bp.route('/patient/<int:patient_id>/add-record/', methods=['GET', 'POST'])
@doctor_login_required
def add_record_for_patient(patient_id):
    doctor = Doctor.query.get(session['user_id'])
    patient = Patient.query.get_or_404(patient_id)

    if request.method == 'POST':
        # --- YAHAN BHI NAYA FILE UPLOAD LOGIC HAI ---
        report_file = request.files.get('report_file')
        filename = None
        if report_file and report_file.filename != '':
            filename = secure_filename(report_file.filename)
            upload_folder = os.path.join(current_app.root_path, 'static/health_reports')
            os.makedirs(upload_folder, exist_ok=True)
            report_file.save(os.path.join(upload_folder, filename))
            
        new_record = MedicalRecord(
            doctor_id=doctor.id,
            patient_id=patient.id,
            symptoms=request.form.get('symptoms'),
            diagnosis=request.form.get('diagnosis'),
            prescription=request.form.get('prescription'),
            dose=request.form.get('dose'),
            report_file=filename # Database me file ka naam save karein
        )
        db.session.add(new_record)
        db.session.commit()
        flash('Medical record added successfully!', 'success')
        return redirect(url_for('doctor.search_patient'))

    return render_template('add_record_form.html', patient=patient)
    
@doctor_bp.route('/profile/')
@doctor_login_required
def profile():
    doctor = Doctor.query.get(session['user_id'])
    return render_template('doctor_profile.html', doctor=doctor)

@doctor_bp.route('/profile/edit/', methods=['GET', 'POST'])
@doctor_login_required
def edit_profile():
    doctor = Doctor.query.get(session['user_id'])
    
    if request.method == 'POST':
        # Form se saara data update karein
        doctor.name = request.form.get('name')
        doctor.gender = request.form.get('gender')
        
        # --- YAHAN PAR FIX HAI ---
        # Date ko check karein
        dob = request.form.get('date_of_birth')
        doctor.date_of_birth = dob if dob else None # Agar dob khaali hai, toh None save karein

        doctor.phone = request.form.get('phone')
        
        # Experience ko check karein
        exp = request.form.get('experience')
        doctor.experience = int(exp) if exp else None # Agar experience khaali hai, toh None save karein

        doctor.registration_no = request.form.get('registration_no')
        doctor.affiliation = request.form.get('affiliation')
        doctor.clinic_address = request.form.get('clinic_address')
        doctor.consultation_hours = request.form.get('consultation_hours')
        doctor.languages_spoken = request.form.get('languages_spoken')
        doctor.consultation_modes = request.form.get('consultation_modes')
        doctor.qualifications = request.form.get('qualifications')
        
        # --- YAHAN FILE UPLOAD KA SAHI LOGIC HAI ---
        profile_pic = request.files.get('profile_picture')
        if profile_pic and profile_pic.filename != '':
            filename = secure_filename(profile_pic.filename)
            # File ko 'app/static/uploads/doctor_dps/' folder me save karein
            upload_folder = os.path.join(current_app.root_path, 'static/uploads/doctor_dps')
            os.makedirs(upload_folder, exist_ok=True) # Agar folder na ho toh banayein
            profile_pic.save(os.path.join(upload_folder, filename))
            # Database me sirf file ka naam save karein
            doctor.profile_picture = filename
            
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('doctor.profile'))

    return render_template('edit_doctor_profile.html', doctor=doctor)


@doctor_bp.route('/manage-conditions/', methods=['GET', 'POST'])
@doctor_login_required
def manage_conditions():
    if request.method == 'POST':
        patient_id = request.form.get('patient')
        condition_name = request.form.get('condition_name')
        start_date = request.form.get('start_date')

        patient = Patient.query.get(patient_id)
        if patient:
            new_condition = PatientCondition(
                patient_id=patient.id,
                condition_name=condition_name,
                start_date=start_date
            )
            db.session.add(new_condition)
            db.session.commit()
            flash('Condition added successfully.', 'success')
        return redirect(url_for('doctor.manage_conditions'))

    # GET request ke liye
    all_patients = Patient.query.all()
    active_conditions = PatientCondition.query.filter(PatientCondition.end_date.is_(None)).order_by(PatientCondition.start_date.desc()).all()

    return render_template('manage_conditions.html', patients=all_patients, active_conditions=active_conditions)