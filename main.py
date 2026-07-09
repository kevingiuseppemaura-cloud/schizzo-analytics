from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import database_stadi
from cachetools import TTLCache

app = FastAPI(title="Schizzo Analytics Engine")

# Cache per evitare chiamate ripetitive allo stesso match
cache_partite = TTLCache(maxsize=100, ttl=60)

class MatchRequest(BaseModel):
    home: str
    away: str
    match_id: str
    arbitro_severity: float = 2.0 

def calcola_impatto_stadio(stadio_info, meteo_avverso=False):
    """
    Moltiplicatore ambientale: 
    - 0.9 = Stadio coperto (protegge da meteo avverso)
    - 1.15 = Stadio aperto + meteo avverso (aumenta falli/cartellini)
    - 1.0 = Standard
    """
    if stadio_info.get("coperto", False):
        return 0.9
    elif meteo_avverso:
        return 1.15
    return 1.0

def get_consenso_mercato(match_id):
    """
    Modulo di integrazione mercati. 
    In futuro qui potrai collegare scraper o API per quote reali.
    """
    # Simulazione dati: Ritorna una probabilità implicita basata su media quote
    return 0.52 

@app.post("/predict")
def predict(request: MatchRequest):
    home_key = request.home.lower().strip()
    away_key = request.away.lower().strip()
    
    if home_key not in database_stadi.DB_STADI or away_key not in database_stadi.DB_STADI:
        raise HTTPException(status_code=404, detail="Squadra non presente nel DB")
        
    home_info = database_stadi.DB_STADI[home_key]
    away_info = database_stadi.DB_STADI[away_key]
    
    # 1. Calcolo Rischio Cartellini
    multiplicatore = calcola_impatto_stadio(home_info)
    base = (home_info["media_cartellini"] + away_info["media_cartellini"]) / 2
    rischio_cartellini = round(((base + request.arbitro_severity) / 2) * multiplicatore, 2)
    
    # 2. Integrazione Mercato
    prob_mercato = get_consenso_mercato(request.match_id)
    
    # 3. Analisi Value Bet (Logica semplice)
    is_value_bet = "Alta" if rischio_cartellini > 2.5 else "Normale"
    
    return {
        "match": f"{request.home} vs {request.away}",
        "rischio_cartellini": rischio_cartellini,
        "livello_rischio": is_value_bet,
        "consenso_mercato_prob": prob_mercato,
        "status": "Analisi completata"
    }