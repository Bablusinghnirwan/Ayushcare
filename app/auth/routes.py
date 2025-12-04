from flask import render_template, redirect, url_for, request, flash, session, jsonify
import random
from app.models import Patient, Doctor
from app import db, bcrypt
from flask import Blueprint # Make sure Blueprint is imported

# Step 2: CREATE the blueprint variable
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup/', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        aadhar = request.form.get('aadhar')
        dob = request.form.get('dob')

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_patient = Patient(
            name=name,
            email=email,
            password_hash=hashed_password,
            aadhar_number=aadhar,
            date_of_birth=dob
        )
        db.session.add(new_patient)
        db.session.commit()

        session['user_id'] = new_patient.id
        session['user_type'] = 'patient'
        
        flash('Signup successful! Please complete your profile.', 'success')
        return redirect(url_for('patient.onboarding', step=1))
    
    return redirect(url_for('auth.login')) # Humein yeh template banana hoga

@auth_bp.route('/signup/doctor/', methods=['GET', 'POST'])
def doctor_signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        specialty = request.form.get('specialty')
        password = request.form.get('password')
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        new_doctor = Doctor(
            name=name, email=email, specialty=specialty, password_hash=hashed_password
        )
        db.session.add(new_doctor)
        db.session.commit()
        
        flash('Doctor registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
        
    return redirect(url_for('auth.login')) # Yeh template bhi banana hoga

@auth_bp.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')

        user = None
        if user_type == 'patient':
            user = Patient.query.filter_by(email=email).first()
        elif user_type == 'doctor':
            user = Doctor.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_type'] = user_type
            
            if user_type == 'patient':
                # Check karein agar onboarding adhoora hai
                if not user.onboarding_complete:
                    return redirect(url_for('patient.onboarding', step=1))
                return redirect(url_for('patient.dashboard'))
            elif user_type == 'doctor':
                return redirect(url_for('doctor.dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('login_v2.html') # Yeh template bhi banana hoga

@auth_bp.route('/logout/')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

# app/auth/routes.py me in teeno functions ko replace karein

@auth_bp.route('/api/auth/send-otp', methods=['POST'])
def send_otp_api():
    data = request.get_json()
    aadhaar = data.get('aadhaar')
    role = data.get('role')
    user = None

    if role == 'patient':
        user = Patient.query.filter_by(aadhar_number=aadhaar).first()
    elif role == 'doctor':
        # YAHAN BADLAV HAI: Doctor ko registration_no se dhoondhein
        user = Doctor.query.filter_by(registration_no=aadhaar).first()
    
    if not user:
        return jsonify({'message': 'User with this ID not found.'}), 404

    mock_otp = str(random.randint(100000, 999999))
    session['mock_otp'] = mock_otp
    session['otp_for_user'] = aadhaar # 'aadhaar' field ab user identifier hai
    print(f"--- MOCK OTP for {aadhaar}: {mock_otp} ---")
    return jsonify({'message': f'A mock OTP has been generated: {mock_otp}'}), 200


@auth_bp.route('/api/auth/login', methods=['POST'])
def login_api():
    data = request.get_json()
    aadhaar = data.get('aadhaar')
    otp = data.get('otp')
    role = data.get('role')

    if session.get('mock_otp') != otp or session.get('otp_for_user') != aadhaar:
        return jsonify({'message': 'Invalid OTP. Please try again.'}), 401

    user = None
    if role == 'patient':
        user = Patient.query.filter_by(aadhar_number=aadhaar).first()
    elif role == 'doctor':
        # YAHAN BADLAV HAI: Doctor ko registration_no se dhoondhein
        user = Doctor.query.filter_by(registration_no=aadhaar).first()

    if not user:
        return jsonify({'message': 'User with this ID not found.'}), 404

    session.clear()
    session['user_id'] = user.id
    session['user_type'] = role
    
    redirect_url = url_for('patient.dashboard') if role == 'patient' else url_for('doctor.dashboard')
    return jsonify({'message': 'Login successful!', 'redirect_url': redirect_url}), 200


@auth_bp.route('/api/auth/signup', methods=['POST'])
def signup_api():
    data = request.get_json()
    role = data.get('signup_role')
    email = data.get('email')
    aadhaar = data.get('aadhaar') # Yeh Aadhaar ya Reg. No. ho sakta hai
    password = data.get('password')

    if not all([role, email, aadhaar, password]):
        return jsonify({'message': 'All fields are required.'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    try:
        if role == 'patient':
            if Patient.query.filter_by(email=email).first() or Patient.query.filter_by(aadhar_number=aadhaar).first():
                return jsonify({'message': 'An account with this email or Aadhaar already exists.'}), 409
            
            new_user = Patient(
                name=data.get('name'), email=email, aadhar_number=aadhaar, password_hash=hashed_password
            )
        elif role == 'doctor':
            if Doctor.query.filter_by(email=email).first() or Doctor.query.filter_by(registration_no=aadhaar).first():
                return jsonify({'message': 'An account with this email or Registration No. already exists.'}), 409

            # YAHAN BADLAV HAI: 'aadhaar' ko registration_no me save karein
            new_user = Doctor(
                name=data.get('name'), email=email, registration_no=aadhaar, password_hash=hashed_password, specialty="General"
            )
        else:
            return jsonify({'message': 'Invalid role specified.'}), 400
        
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"--- SIGNUP API ERROR: {e} ---")
        return jsonify({'message': 'Database error, could not create account.'}), 500

    return jsonify({'message': 'Account created successfully!'}), 201