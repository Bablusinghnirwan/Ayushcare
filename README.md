# AyushCare - Flask Version

AyushCare is a comprehensive healthcare platform designed to bridge the gap between patients and doctors. This repository contains the Flask-based backend and frontend implementation of the AyushCare application.

## Features

*   **Patient & Doctor Portals:** Dedicated dashboards for patients and doctors.
*   **Appointment Booking:** Easy scheduling of appointments with doctors.
*   **Medical Records:** Secure storage and access to patient medical history.
*   **AI Chat Assistant:** Intelligent chatbot for preliminary health queries and assistance.
*   **Diet Advisor:** Personalized diet recommendations based on health conditions.
*   **Ingredient Scanner:** OCR-based tool to analyze food product ingredients for safety.
*   **Secure Authentication:** Robust login and signup system for all users.

## Tech Stack

*   **Backend:** Python, Flask
*   **Database:** PostgreSQL (SQLAlchemy ORM)
*   **AI Integration:** Google Gemini API
*   **Frontend:** HTML, CSS, JavaScript (Jinja2 Templates)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Bablusinghnirwan/Ayushcare.git
    cd Ayushcare
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration:**
    *   Set up your environment variables (recommended) or update `config.py` with your database URI and API keys.
    *   Ensure PostgreSQL is running and the database is created.

5.  **Run the application:**
    ```bash
    python run.py
    ```

## Usage

*   Access the application at `http://127.0.0.1:5000/`.
*   Register as a Patient or Doctor to explore the features.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
