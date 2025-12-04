# app/models.py

from . import db  # __init__.py se db object import karein
from sqlalchemy import Enum
import enum
from datetime import datetime

# Django ke choices ke liye Enums banayein (yeh optional hai par aacha practice hai)
class AppointmentModeEnum(enum.Enum):
    IN_CLINIC = 'In-Clinic Visit'
    VIDEO_CALL = 'Video Call'
    AUDIO_CALL = 'Audio Call'

class AppointmentStatusEnum(enum.Enum):
    PENDING_CONFIRMATION = 'Pending Confirmation'
    SCHEDULED = 'Scheduled'
    COMPLETED = 'Completed'
    CANCELLED = 'Cancelled'
    
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # patient_id ko hata sakte hain ya rakh sakte hain, session_id zaroori hai
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False) 
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False) # <--- Naya column
    sender = db.Column(db.String(10), nullable=False)  # 'user' ya 'ai'
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return f'<ChatHistory {self.id}>'

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    start_time = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # Title ko hum pehle message se generate kar sakte hain ya user ko edit karne de sakte hain
    title = db.Column(db.String(100), nullable=True) 

    # Patient model se relationship
    patient = db.relationship('Patient', backref=db.backref('chat_sessions', lazy='dynamic'))
    # History model se relationship
    messages = db.relationship('ChatHistory', backref='session', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<ChatSession {self.id}>'
    
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    aadhar_number = db.Column(db.String(12), unique=True, nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=True)
    profile_picture = db.Column(db.String(100), nullable=True) # File path store karenge

    # Onboarding Fields
    blood_group = db.Column(db.String(5), nullable=True)
    height = db.Column(db.Integer, nullable=True) # cm me
    weight = db.Column(db.Integer, nullable=True) # kg me
    allergies = db.Column(db.Text, nullable=True)
    chronic_diseases = db.Column(db.Text, nullable=True)
    onboarding_complete = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    medical_records = db.relationship('MedicalRecord', backref='patient', lazy=True, cascade="all, delete-orphan")
    conditions = db.relationship('PatientCondition', backref='patient', lazy=True, cascade="all, delete-orphan")
    appointments = db.relationship('Appointment', backref='patient', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Patient {self.name}>'

class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialty = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    experience = db.Column(db.Integer, nullable=True)
    registration_no = db.Column(db.String(50), nullable=True)
    affiliation = db.Column(db.String(200), nullable=True)
    clinic_address = db.Column(db.Text, nullable=True)
    consultation_hours = db.Column(db.String(100), nullable=True)
    languages_spoken = db.Column(db.String(200), nullable=True)
    consultation_modes = db.Column(db.String(200), nullable=True)
    qualifications = db.Column(db.Text, nullable=True)
    profile_picture = db.Column(db.String(100), nullable=True)

    # Relationships
    medical_records = db.relationship('MedicalRecord', backref='doctor', lazy=True)
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)

    def __repr__(self):
        return f'<Doctor {self.name}>'

class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    symptoms = db.Column(db.Text, nullable=True)
    diagnosis = db.Column(db.Text, nullable=True)
    prescription = db.Column(db.Text, nullable=True)
    dose = db.Column(db.String(50), nullable=True)
    record_date = db.Column(db.Date, server_default=db.func.current_date(), nullable=False)
    report_file = db.Column(db.String(100), nullable=True) # File path store karenge

    def __repr__(self):
        return f'<MedicalRecord {self.id}>'

class PatientCondition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    condition_name = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date, server_default=db.func.current_date(), nullable=False)
    end_date = db.Column(db.Date, nullable=True)

    def __repr__(self):
        return f'<PatientCondition {self.condition_name}>'

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    appointment_datetime = db.Column(db.DateTime, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    
    status = db.Column(
        Enum(AppointmentStatusEnum), 
        default=AppointmentStatusEnum.PENDING_CONFIRMATION, 
        nullable=False
    )
    
    mode = db.Column(
        Enum(AppointmentModeEnum), 
        default=AppointmentModeEnum.IN_CLINIC, 
        nullable=False
    )

    def __repr__(self):
        return f'<Appointment {self.id}>'