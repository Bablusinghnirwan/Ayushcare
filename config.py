import os

class Config:
    # Django se SECRET_KEY le liya
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'django-insecure-w%8@yvs0gh+9o+x8bxf$zo)&as-=&+&us+3kabevy%3_r2(5rk'

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'postgresql://postgres:2416@localhost:5432/hospital_db1' 

    # Yeh SQLAlchemy ko behtar performance ke liye set karta hai
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    GEMINI_API_KEY = "AIzaSyCRwket7-YNKahELKwj4yNIIh6eCzja9rk"