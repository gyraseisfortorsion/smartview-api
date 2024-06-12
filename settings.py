from dotenv import load_dotenv
import os

# Load the .env file
load_dotenv()

class Config:
    DATABASE_URL = os.getenv('DATABASE_URL')
    AIRDATA_API_KEY = os.getenv('AIRDATA_API_KEY')


config=Config()