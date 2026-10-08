# Asegura que `app` sea importable al correr pytest desde la raíz del repo.
from gate.env import load_dotenv

# The AI tests (`pytest -m ai`) read GEMINI_API_KEY at import: load the local .env first.
load_dotenv()
