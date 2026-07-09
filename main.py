from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import database_stadi
import scraper  # Importiamo il tuo nuovo modulo
from cachetools import TTLCache

app = FastAPI(title="Schizzo Analytics Engine V4.0")

# Cache per le richieste al motore di analisi
cache_previsioni = TTLCache(maxsize=100, ttl=300)

class MatchRequest(BaseModel):
    home: str
    away: str
    match_id: str  # ID necessario per lo scraper di Flashscore
    arbitro_severity: float = 2.0 

def calcola_impatto_stadio(stadio_info, meteo_avverso=False):
    """
    Applica il moltiplicatore ambientale:
    - 0.9: Stadio coperto (protezione massima)
    - 1.15: Stadio aperto + meteo avverso (aumento falli)
    - 1.0: Condizioni standard
    """
    if stadio_info.get("coperto", False):
        return 0.9
    elif meteo_avverso:
        return 1.15
    return 1.0

@app.post("/predict")
def predict(request: MatchRequest):
    home_key = request.home.lower().strip()
    away_key = request.away.lower().strip()
    
    # Validazione squadre nel DB
    if home_key not in database_stadi.DB_STADI or away_key not in database_stadi.DB_STADI:
        raise HTTPException(status_code=404, detail="Una delle squadre non è presente nel database.")
        
    home_info = database_stadi.DB_STADI[home_key]
    away_info = database_stadi.DB_STADI[away_key]
    
    # 1. Calcolo Rischio Cartellini (Logica Statistica + Ambientale)
    multiplicatore = calcola_impatto_stadio(home_info)
    base = (home_info["media_cartellini"] + away_info["media_cartellini"]) / 2
    rischio_cartellini = round(((base + request.arbitro_severity) / 2) * multiplicatore, 2)
    
    # 2. Recupero dati dal mercato (Web Scraping ottimizzato)
    # Lo scraper gestisce internamente cache e tempi di attesa
    quota_reale = scraper.get_quote_flashscore(request.match_id)
    prob_mercato = round(1 / quota_reale, 3)
    
    # 3. Analisi Value Bet
    # Confrontiamo la nostra previsione (standardizzata) con la probabilità del mercato
    is_value = "Opportunity" if (rischio_cartellini / 5) > prob_mercato else "Allineato"
    
    return {
        "match": f"{request.home} vs {request.away}",
        "rischio_cartellini": rischio_cartellini,
        "probabilita_mercato_implicita": prob_mercato,
        "analisi_valore": is_value,
        "status": "Analisi completata con successo"
    }