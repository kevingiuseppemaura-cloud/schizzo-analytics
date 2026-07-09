from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import database_stadi

app = FastAPI(title="Schizzo Analytics Cloud")

class MatchRequest(BaseModel):
    home: str
    away: str
    match_id: str = None  # Reso opzionale per permettere la ricerca automatica

def estrai_dati_flashscore(match_id):
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

def cerca_match_id_automatico(home_name, away_name):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.flashscore.com/",
        "x-fsign": "SW9D1eZo"
    }
    url = "https://d.flashscore.com/x/feed/tr_1_1" 
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.text.split('¬')
        for line in data:
            if home_name.lower() in line.lower() and away_name.lower() in line.lower():
                parts = line.split('÷')
                return parts[1]
        return None
    except Exception:
        return None

@app.post("/predict")
def predict(request: MatchRequest):
    # Logica di ricerca automatica se match_id non viene fornito
    if not request.match_id:
        request.match_id = cerca_match_id_automatico(request.home, request.away)
        
    if not request.match_id:
        raise HTTPException(status_code=404, detail="Partita non trovata o ID mancante")
    
    home_key = request.home.lower().strip()
    dati_live = estrai_dati_flashscore(request.match_id)
    stadio_info = database_stadi.DB_STADI.get(home_key, {"stadio": "Sconosciuto", "citta": "N/D", "campo": "N/D", "indice_coach": 0})
    
    if not dati_live:
        raise HTTPException(status_code=404, detail="Dati live non disponibili per questo ID")

    data_match = dati_live.get('DATA', {})
    
    return {
        "stadium": stadio_info["stadio"],
        "city": stadio_info["citta"],
        "field_type": stadio_info["campo"],
        "coach_impact": stadio_info["indice_coach"],
        "referee": data_match.get('referee', 'N/D'),
        "prob_1": 45.0, 
        "data_live_raw": f"{data_match.get('home_name')} vs {data_match.get('away_name')}",
        "status": "Dati Real-Time Integrati con Automazione"
    }