from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import database_stadi

app = FastAPI(title="Schizzo Analytics Cloud")

class MatchRequest(BaseModel):
    home: str
    away: str
    match_id: str  # Aggiungiamo il match_id per la chiamata reale

def estrai_dati_flashscore(match_id):
    """Funzione integrata di scraping dal tuo scraper.py."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "x-fsign": "SW9D1eZo",
        "Referer": "https://www.flashscore.com/"
    }
    url = f"https://d.flashscore.com/x/feed/df_st_1_{match_id}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return response.json()
    except Exception:
        return None

@app.post("/predict")
def predict(request: MatchRequest):
    home_key = request.home.lower().strip()
    
    # 1. Recupero dati reali
    dati_live = estrai_dati_flashscore(request.match_id)
    stadio_info = database_stadi.DB_STADI.get(home_key, {"stadio": "Sconosciuto", "citta": "N/D"})
    
    if not dati_live:
        raise HTTPException(status_code=404, detail="Dati live non disponibili per questo ID")

    # 2. Struttura dati arricchita con i dati reali
    data_match = dati_live.get('DATA', {})
    
    return {
        "stadium": stadio_info["stadio"],
        "city": stadio_info["citta"],
        "referee": data_match.get('referee', 'N/D'),
        "prob_1": 45.0, # Placeholder per ora, integreremo il calcolo reale dopo
        "data_live_raw": data_match.get('home_name') + " vs " + data_match.get('away_name'),
        "status": "Dati Real-Time Integrati"
    }