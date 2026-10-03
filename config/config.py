import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret_key')
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'abhyas_ai_secret_key_2026')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    DATA_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')

    # Chroma Cloud Configuration
    CHROMA_HOST = os.getenv('CHROMA_HOST', 'api.trychroma.com')
    CHROMA_API_KEY = os.getenv('CHROMA_API_KEY', '')
    CHROMA_TENANT = os.getenv('CHROMA_TENANT', '688bc2df-d727-4a69-9f2e-5fa46471ce1c')
    CHROMA_DATABASE = os.getenv('CHROMA_DATABASE', 'abhyasAI')

    # Ingestion & Upload Limits
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '25'))
    MAX_FILES_PER_SESSION = int(os.getenv('MAX_FILES_PER_SESSION', '3'))
    MAX_CONTENT_LENGTH = MAX_FILE_SIZE_MB * 1024 * 1024 * MAX_FILES_PER_SESSION
