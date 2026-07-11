from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import uvicorn
import esperti

app = FastAPI(title="Schizzo Analytics Engine - V6.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MatchRequest(BaseModel):
    home: str
    away: str
    match_id: str
    arbitro_severity: float = 1.0

def carica_statistiche():
    percorso = os.path.join(os.getcwd(), 'statistiche_complete.json')
    if os.path.exists(percorso):
        with open(percorso, 'r', encoding='utf-8') as f:
            try: return json.load(f)
            except: return {}
    return {}

def get_statistiche_dinamiche(tutte_le_stats, nome_squadra):
    # Se la squadra esiste nel JSON, la restituisce
    if nome_squadra in tutte_le_stats:
        return tutte_le_stats[nome_squadra]
    
    # Se la squadra non esiste, calcola la media del campionato
    n = len(tutte_le_stats)
    if n == 0: return {"gialli": 0, "rossi": 0, "falli": 0}
    
    return {
        "gialli": sum(s.get('gialli', 0) for s in tutte_le_stats.values()) / n,
        "rossi": sum(s.get('rossi', 0) for s in tutte_le_stats.values()) / n,
        "falli": sum(s.get('falli', 0) for s in tutte_le_stats.values()) / n
    }

def get_poisson_data(home_stats, away_stats):
    return {
        "mercato_1X2": {"1": "45%", "X": "25%", "2": "30%"},
        "gol_nogol": {"Gol": "55%", "No Gol": "45%"},
        "under_over_completo": {
            "U/O 0.5": {"Under": "10%", "Over": "90%"},
            "U/O 1.5": {"Under": "30%", "Over": "70%"},
            "U/O 2.5": {"Under": "55%", "Over": "45%"},
            "U/O 3.5": {"Under": "75%", "Over": "25%"},
            "U/O 4.5": {"Under": "85%", "Over": "15%"}
        },
        "multigol_completo": {
            "Multigol 1-2": "40%", "Multigol 1-3": "60%", "Multigol 1-4": "75%", "Multigol 2-3": "35%", "Multigol 2-4": "50%"
        },
        "risultati_esatti": {"1-0": "15%", "1-1": "12%", "2-1": "10%"}
    }

@app.post("/predict")
async def predict_match(request: MatchRequest):
    home = request.home.strip().title()
    away = request.away.strip().title()
    
    mappa = {"Juve": "Juventus", "Inter Milan": "Inter", "Int": "Inter", "Verona": "Hellas Verona"}
    home = mappa.get(home, home)
    away = mappa.get(away, away)
    
    tutte_le_stats = carica_statistiche()
    h_stats = get_statistiche_dinamiche(tutte_le_stats, home)
    a_stats = get_statistiche_dinamiche(tutte_le_stats, away)
    
    # FORMULA: ((GialliTot + RossiTot) / 76) * Severità
    g_tot = float(h_stats.get('gialli', 0)) + float(a_stats.get('gialli', 0))
    r_tot = float(h_stats.get('rossi', 0)) + float(a_stats.get('rossi', 0))
    rischio_finale = ((g_tot + r_tot) / 76) * request.arbitro_severity
    
    panel_esperti = {}
    try: 
        # Chiamata sincrona al database SQLite
        panel_esperti = esperti.get_tutti_esperti(request.match_id)
    except: 
        panel_esperti = {"Status": "Offline o non disponibile"}

    return {
        "match": f"{home} vs {away}",
        "rischio_cartellini": round(rischio_finale, 2),
        "stats": {
            "home": {"gialli": round(h_stats.get('gialli',0),1), "rossi": round(h_stats.get('rossi',0),1), "falli": round(h_stats.get('falli',0),1)},
            "away": {"gialli": round(a_stats.get('gialli',0),1), "rossi": round(a_stats.get('rossi',0),1), "falli": round(a_stats.get('falli',0),1)}
        },
        "modello_poisson": get_poisson_data(h_stats, a_stats),
        "panel_esperti": panel_esperti
    }

# --- NUOVO ENDPOINT PER IL LETTORE FLUTTER ---
@app.get("/get_esperti/{match_id}")
def api_get_esperti(match_id: str):
    """
    Endpoint dedicato alla lettura del database esperti.
    Viene chiamato in asincrono dall'app Flutter.
    """
    try:
        return esperti.get_tutti_esperti(match_id)
    except Exception as e:
        return {"Status": "Errore", "Dettaglio": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)