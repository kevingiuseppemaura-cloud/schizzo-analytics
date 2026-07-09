from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import database_stadi
from cachetools import TTLCache
import math

app = FastAPI(title="Schizzo Analytics Engine V3.4")
cache_partite = TTLCache(maxsize=100, ttl=60)

class MatchRequest(BaseModel):
    home: str
    away: str
    match_id: str = None
    arbitro_severity: float = 2.0  # Media cartellini arbitro (default 2.0)

def calcola_impatto_stadio(stadio_info, meteo_avverso=False):
    # Logica: lo stadio coperto protegge il gioco riducendo l'impatto di meteo avverso
    if stadio_info.get("coperto", False):
        return 0.9
    elif meteo_avverso:
        return 1.15
    return 1.0

def stima_rischio_cartellini(home_info, away_info, arbitro_severity, moltiplicatore_meteo):
    # Base: media ponderata delle due squadre + severità arbitro
    base = (home_info["media_cartellini"] + away_info["media_cartellini"]) / 2
    rischio = (base + arbitro_severity) / 2
    # Applichiamo il fattore ambientale
    return round(rischio * moltiplicatore_meteo, 2)

@app.post("/predict")
def predict(request: MatchRequest):
    home_key = request.home.lower().strip()
    away_key = request.away.lower().strip()
    
    if home_key not in database_stadi.DB_STADI or away_key not in database_stadi.DB_STADI:
        raise HTTPException(status_code=404, detail="Squadra non trovata nel DB")
        
    home_info = database_stadi.DB_STADI[home_key]
    
    # Calcolo ambientale (simuliamo meteo_avverso=False per ora, puoi passarlo nel JSON)
    moltiplicatore = calcola_impatto_stadio(home_info, meteo_avverso=False)
    
    # Calcolo cartellini
    rischio_cartellini = stima_rischio_cartellini(
        home_info, 
        database_stadi.DB_STADI[away_key], 
        request.arbitro_severity, 
        moltiplicatore
    )
    
    return {
        "match": f"{request.home} vs {request.away}",
        "environment_factor": moltiplicatore,
        "prediction": {
            "risk_cards": rischio_cartellini,
            "level": "Alta" if rischio_cartellini > 2.5 else "Normale"
        }
    }