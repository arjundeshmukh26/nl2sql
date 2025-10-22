import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv("config.env")


class Settings:
    # Database
    database_url: str = os.getenv("DATABASE_URL", "")
    
    # Gemini API
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    
    # App Settings
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Query limits
    max_query_results: int = 1000
    


settings = Settings()