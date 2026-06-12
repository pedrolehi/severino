import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY não está configurado")
if not REDIS_PASSWORD:
    raise ValueError("REDIS_PASSWORD não está configurado")
