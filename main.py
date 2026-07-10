from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import uvicorn
import esperti

app = FastAPI(title="Schizzo Analytics Engine - V5.9 Formula 76")

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
            "Multigol 1-2": "40%",
            "Multigol 1-3": "60%",
            "Multigol 1-4": "75%",
            "Multigol 2-3": "35%",
            "Multigol 2-4": "50%"
        },
        "risultati_esatti": {
            "1-0": "15%",
            "1-1": "12%",
            "2-1": "10%"
        },
        "xG": {"home": 1.5, "away": 1.2}
    }

@app.post("/predict")
async def predict_match(request: MatchRequest):
    home = request.home.strip().title()
    away = request.away.strip().title()
    
    mappa = {"Juve": "Juventus", "Inter Milan": "Inter", "Int": "Inter", "Verona": "Hellas Verona"}
    home = mappa.get(home, home)
    away = mappa.get(away, away)
    
    tutte_le_stats = carica_statistiche()
    default = {"gialli": 60, "rossi": 3, "falli": 450}
    
    h_stats = tutte_le_stats.get(home, default)
    a_stats = tutte_le_stats.get(away, default)
    
    # NUOVA FORMULA: (Totale Gialli + Rossi / 76) * Severità
    totale_gialli = float(h_stats.get('gialli', 0)) + float(a_stats.get('gialli', 0))
    totale_rossi = float(h_stats.get('rossi', 0)) + float(a_stats.get('rossi', 0))
    
    rischio_finale = ((totale_gialli + totale_rossi) / 76) * request.arbitro_severity
    
    # Dati Poisson
    dati_poisson = get_poisson_data(h_stats, a_stats)
    
    # Panel Esperti
    try:
        panel_esperti = await esperti.get_tutti_esperti(request.match_id)
    except Exception:
        panel_esperti = {"Status": "Errore caricamento esperti"}
    
    print(f"DEBUG -> Formula: ({totale_gialli}G + {totale_rossi}R) / 76 * {request.arbitro_severity} = {rischio_finale:.2f}")

    return {
        "match": f"{home} vs {away}",
        "rischio_cartellini": round(rischio_finale, 2),
        "stats": {
            "home": {
                "gialli": h_stats.get('gialli'), 
                "rossi": h_stats.get('rossi'), 
                "falli": h_stats.get('falli')
            },
            "away": {
                "gialli": a_stats.get('gialli'), 
                "rossi": a_stats.get('rossi'), 
                "falli": a_stats.get('falli')
            }
        },
        "modello_poisson": dati_poisson,
        "panel_esperti": panel_esperti
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)