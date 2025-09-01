import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-key-for-hackathon-only'
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or 'mysql+mysqlconnector://username:password@localhost/mood_journal'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    HUGGING_FACE_API_KEY = os.getenv('HUGGING_FACE_API_KEY')