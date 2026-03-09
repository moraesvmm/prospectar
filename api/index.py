from backend.main import app
from backend.database import init_db

# Initialize database tables for Vercel
init_db()
