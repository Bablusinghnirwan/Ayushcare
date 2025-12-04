from flask import render_template, redirect, url_for, request, session, jsonify, current_app, flash
from app.models import Patient, Doctor, Appointment, MedicalRecord, PatientCondition, ChatHistory, ChatSession
from datetime import datetime, timezone
from app import db
import google.generativeai as genai
from flask import Blueprint # Make sure Blueprint is imported
import json
import traceback

# 2. CREATE the blueprint variable right after the imports
main_bp = Blueprint('main', __name__)

# Patient login decorator yahan bhi copy kar sakte hain ya common utils file me daal sakte hain
from functools import wraps
def patient_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'patient':
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@main_bp.route('/')
def home():
    if 'user_id' in session:
        if session['user_type'] == 'patient':
            return redirect(url_for('patient.dashboard'))
        else:
            return redirect(url_for('doctor.dashboard'))
    return redirect(url_for('auth.login'))

# In app/main/routes.py

@main_bp.route('/api/chat/', methods=['POST'])
@patient_login_required
def chat_api():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    user_message = data['message']
    patient = Patient.query.get(session['user_id'])
    
    # --- Get current chat session ID ---
    # Use session_id from request if provided, otherwise use the one stored in Flask session
    current_session_id = data.get('session_id') or session.get('current_chat_session_id') 
    
    if not current_session_id:
         # Attempt to get the latest session for the user if none is active
         latest_session = ChatSession.query.filter_by(patient_id=patient.id).order_by(ChatSession.start_time.desc()).first()
         if latest_session:
             current_session_id = latest_session.id
             session['current_chat_session_id'] = current_session_id # Store it for future requests
         else:
             # If still no session, create a new one (should ideally not happen if dashboard logic is correct)
             new_session = ChatSession(patient_id=patient.id, title="New Chat") 
             db.session.add(new_session)
             db.session.commit()
             current_session_id = new_session.id
             session['current_chat_session_id'] = current_session_id
             print(f"WARN: Created a new session {current_session_id} from chat_api")


    # 1. Save User's Message to the correct session
    user_chat = ChatHistory(patient_id=patient.id, session_id=current_session_id, sender='user', message=user_message)
    db.session.add(user_chat)
    
    # --- Fetch Previous Chat History from the CURRENT session ---
    prev_chats = ChatHistory.query.filter_by(session_id=current_session_id).order_by(ChatHistory.timestamp.asc()).limit(10).all() # Get last 10 messages of this session
    formatted_history = "\n".join([f"{chat.sender.upper()}: {chat.message}" for chat in prev_chats])
    
    # --- Fetch Medical History ---
    records = MedicalRecord.query.filter_by(patient_id=patient.id).order_by(MedicalRecord.record_date.desc()).all()
    conditions = PatientCondition.query.filter_by(patient_id=patient.id).order_by(PatientCondition.start_date.desc()).all()

    medical_history_text = f"Patient Name: {patient.name}, DOB: {patient.date_of_birth.strftime('%Y-%m-%d') if patient.date_of_birth else 'N/A'}\n"
    medical_history_text += "Active Conditions:\n"
    active_conditions_list = [cond for cond in conditions if cond.end_date is None]
    if active_conditions_list:
        for cond in active_conditions_list:
            medical_history_text += f"- {cond.condition_name} (since {cond.start_date.strftime('%Y-%m-%d')})\n"
    else:
        medical_history_text += "- No active conditions recorded.\n"
    
    medical_history_text += "\nPast Medical Records:\n"
    if records:
        for rec in records:
            doctor_name = rec.doctor.name if rec.doctor else "Unknown Doctor" 
            medical_history_text += f"- Date: {rec.record_date.strftime('%Y-%m-%d')}, Doctor: {doctor_name}, Symptoms: {rec.symptoms or 'N/A'}, Diagnosis: {rec.diagnosis or 'N/A'}\n"
    else:
        medical_history_text += "- No past medical records found.\n"
        
    # --- Fetch Upcoming Appointments ---
    now = datetime.now(timezone.utc) 
    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient.id,
        Appointment.appointment_datetime > now,
        Appointment.status.in_(['SCHEDULED', 'PENDING_CONFIRMATION']) 
    ).order_by(Appointment.appointment_datetime.asc()).all()

    appointment_text = "\nUpcoming Appointments:\n"
    if upcoming_appointments:
        for appt in upcoming_appointments:
            doctor_name = appt.doctor.name if appt.doctor else "Unknown Doctor"
            appt_time_str = appt.appointment_datetime.strftime('%Y-%m-%d at %I:%M %p') 
            appointment_text += f"- With Dr. {doctor_name} on {appt_time_str}, Mode: {appt.mode.value}, Status: {appt.status.value}\n"
    else:
        appointment_text += "- No upcoming appointments scheduled.\n"

    # --- Combine Medical History and Appointments ---
    full_history_text = medical_history_text + appointment_text

    # --- Debugging ---
    print("--- CONTEXT SENT TO AI ---")
    print("Session ID:", current_session_id)
    print("Past Chat:\n", formatted_history)
    print("\nFull History (Medical + Appointments):\n", full_history_text) 
    print("-----------------------------")

    ai_response = "Error: AI response not generated." # Default error response

    try:
        genai.configure(api_key=current_app.config['GEMINI_API_KEY'])
        model = genai.GenerativeModel('gemini-pro-latest') # Use your working model name

        prompt = f"""
        You are a helpful medical AI assistant for 'Vaidyashri'.
        Your knowledge is strictly limited to the patient data (including upcoming appointments) AND the PAST CHAT HISTORY provided below.
        Use the Past Chat History to understand the context. Use the Upcoming Appointments section to answer appointment-related questions.
        
        You must differentiate between two types of questions:
        1.  **Factual History Questions:** (e.g., "Who was my last doctor?", "When is my next appointment?") Answer directly from the data/past chat. DO NOT add warnings.
        2.  **Medical Advice Questions:** (e.g., "I have a headache")
        
        Your task:
        -   Answer Factual History Questions directly.
        -   For Medical Advice Questions about symptoms in the 'Safe Medicine List', check active conditions. If no conflict, suggest the medicine AND start response with [ADVICE] and end with "Lekin, ... doctor se zaroor poochein."
        -   For other advice questions, give general safe response, start with [ADVICE] and end with the doctor warning.

        --- SAFE MEDICINE LIST START ---
        - Headache (Sar Dard): Paracetamol
        - Common Cold (Sardi/Zukam): Cetirizine
        - Acidity (Gas): Antacid Gel
        - General Body Pain: Paracetamol
        --- SAFE MEDICINE LIST END ---

        --- PAST CHAT HISTORY START ---
        {formatted_history}
        --- PAST CHAT HISTORY END ---

        --- PATIENT'S MEDICAL DATA & APPOINTMENTS START ---
        {full_history_text} 
        --- PATIENT'S MEDICAL DATA & APPOINTMENTS END ---

        PATIENT'S CURRENT QUESTION: "{user_message}"

        ASSISTANT'S RESPONSE (in Hinglish):
        """

        response = model.generate_content(prompt)
        ai_response = response.text.strip() # Get AI response

        # 2. Save AI's response to the correct session
        ai_chat = ChatHistory(patient_id=patient.id, session_id=current_session_id, sender='ai', message=ai_response)
        db.session.add(ai_chat)

        # 3. Commit both user and AI messages
        db.session.commit()

        # Update session title if it's a new chat
        current_session_obj = ChatSession.query.get(current_session_id)
        if current_session_obj and current_session_obj.title == "New Chat" and len(prev_chats) <= 1: # Only update title for the very first message pair
             try:
                 # Ask AI to summarize the first user message into a title
                 title_prompt = f"Summarize the following user query into a short chat title (max 5 words): '{user_message}'"
                 title_response = model.generate_content(title_prompt)
                 new_title = title_response.text.strip().replace('"', '') # Remove quotes
                 if new_title:
                     current_session_obj.title = new_title
                     db.session.commit()
             except Exception as title_e:
                 print(f"Could not generate title: {title_e}") # Don't crash if title generation fails
            
    except Exception as e:
        db.session.rollback() # Rollback if error occurs during AI call or saving
        ai_response = "Sorry, AI service is currently unavailable."
        print(f"AI API Error: {e}")
        traceback.print_exc()

    return jsonify({'reply': ai_response})

# app/main/routes.py me is function ko poora replace karein

@main_bp.route('/book-appointment/', methods=['GET', 'POST'])
@patient_login_required # Is page ke liye login zaroori hai
def book_appointment():
    # POST LOGIC (JAB FORM SUBMIT HOGA)
    if request.method == 'POST':
        doctor_id = request.form.get('doctor')
        # datetime ko combine karein
        appointment_datetime_str = f"{request.form.get('date')} {request.form.get('time')}"
        
        new_appointment = Appointment(
            patient_id=session['user_id'],
            doctor_id=doctor_id,
            appointment_datetime=appointment_datetime_str,
            reason=request.form.get('reason'),
            mode=request.form.get('mode'),
            status='SCHEDULED' # Ya 'PENDING_CONFIRMATION'
        )
        db.session.add(new_appointment)
        db.session.commit()
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('main.book_appointment'))

    # GET LOGIC (JAB PAGE LOAD HOGA) - YAHAN PAR FIX HAI
    # Dropdown ke liye saare doctors fetch karein
    doctors = Doctor.query.all()
    # Current patient ke saare appointments fetch karein
    appointments = Appointment.query.filter_by(patient_id=session['user_id']).order_by(Appointment.appointment_datetime.desc()).all()

    # Dono lists ko template ko bhejein
    return render_template('book_appointment.html', doctors=doctors, appointments=appointments)

@main_bp.route('/records/')
@patient_login_required
def medical_records():
    # This logic is from your Django views.py
    patient = Patient.query.get(session['user_id'])
    records = MedicalRecord.query.filter_by(patient_id=patient.id).order_by(MedicalRecord.record_date.desc()).all()

    # We need to create a 'records.html' template next
    return render_template('records.html', patient=patient, records=records)


# In app/main/routes.py

@main_bp.route('/api/diet-advice/', methods=['POST'])
def diet_advice_api():
    try:
        data = request.get_json()
        disease = data.get('disease')
        medicine = data.get('medicine')
        lang = data.get('language', 'en')

        genai.configure(api_key=current_app.config['GEMINI_API_KEY'])

        model = genai.GenerativeModel(
            'gemini-pro-latest', # Correct model name
            generation_config={"response_mime_type": "application/json"}
        )

        full_prompt = f"""
        You are an expert dietician. Your response MUST be in the {lang} language.
        Generate a list of foods to 'avoid' and 'recommend' based on the user's query.
        Structure your response ONLY as a single, valid JSON object with "avoid" and "recommend" keys, which are arrays of strings.

        User Query:
        - Disease: {disease}
        - Optional Medicine: {medicine or 'None'}
        """

        response = model.generate_content(full_prompt)
        return jsonify(json.loads(response.text))

    except Exception as e:
        print(f"Error in diet_advice_api: {e}")
        return jsonify({'error': 'Failed to get advice from AI.'}), 500
    
@main_bp.route('/diet-advisor/')
def diet_advisor():
    # This function just needs to show the diet advisor page
    return render_template('diet_advisor.html')

# In app/main/routes.py

@main_bp.route('/scanner/')
def scanner():
    # This function just needs to show the scanner page
    return render_template('scanner.html')

@main_bp.route('/api/analyze-ingredients/', methods=['POST'])
@patient_login_required
def analyze_ingredients_api():
    if 'file' not in request.files:
        return jsonify({"error": "No image file provided."}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file."}), 400

    try:
        # NOTE: easyocr ko install karna zaroori hai: pip install easyocr
        import easyocr
        reader = easyocr.Reader(['en'])

        patient = Patient.query.get(session['user_id'])
        
        active_conditions = PatientCondition.query.filter_by(patient_id=patient.id, end_date=None).all()
        
        health_profile = {
            "conditions": [cond.condition_name for cond in active_conditions],
            "allergies": patient.allergies.split(',') if patient.allergies else []
        }
        
        image_bytes = file.read()
        raw_text = " ".join(reader.readtext(image_bytes, detail=0, paragraph=True))
        
        if not raw_text:
            return jsonify({"error": "Could not detect any text on the label."}), 400

        genai.configure(api_key=current_app.config['GEMINI_API_KEY'])
        model = genai.GenerativeModel('gemini-pro-latest') # Sahi model naam

        prompt = f"""
        You are an expert AI Nutritionist for AyushCare.
        - User Health Profile: {json.dumps(health_profile)}
        - Raw OCR Text from Product Package: "{raw_text}"
        TASK:
        1. Locate the ingredients list in the Raw OCR Text.
        2. Compare each ingredient against the user's health profile.
        3. Provide a final verdict: "Safe", "Eat in Moderation", or "Not Recommended".
        4. Write a concise reason.
        5. List the specific ingredients you identified as risky.
        6. Suggest 1-2 safer alternative product types if the product is not "Safe".
        7. You MUST output your response ONLY as a single, valid JSON object with keys: "status", "reason", "risky_ingredients", "suggestions".
        """
        
        response = model.generate_content(prompt)
        # Clean the response to ensure it's valid JSON
        cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '')
        analysis_result = json.loads(cleaned_response_text)

        return jsonify({
            "health_analysis": analysis_result,
            "patient_name": patient.name
        })

    except Exception as e:
        print(f"Error in analyze_ingredients_api: {e}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500
    

# app/main/routes.py me yeh function add karein

@main_bp.route('/condition/edit/<int:condition_id>/', methods=['GET', 'POST'])
def edit_condition(condition_id):
    # Yeh function doctor aur patient dono istemal kar sakte hain, isliye login check zaroori hai
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    condition = PatientCondition.query.get_or_404(condition_id)

    # POST LOGIC (Jab form submit hoga)
    if request.method == 'POST':
        end_date_str = request.form.get('end_date')
        if end_date_str:
            condition.end_date = end_date_str
            db.session.commit()
            flash('Condition marked as completed.', 'success')

        # Agar doctor hai toh doctor dashboard par bhejein
        if session.get('user_type') == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        # Warna patient dashboard par bhejein
        else:
            return redirect(url_for('patient.dashboard'))

    # GET LOGIC (Jab page pehli baar khulega)
    return render_template('edit_condition.html', condition=condition)