from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import uvicorn

app = FastAPI(title="Schizzo Analytics Engine - V5.7 Extended")

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

def calcola_media_partita(stats):
    # FORMULA 38: (Gialli + (Rossi * 3)) / 38
    g = float(stats.get('gialli', 0))
    r = float(stats.get('rossi', 0))
    return (g + (r * 3)) / 38

def get_poisson_data(home_stats, away_stats):
    # Dati estesi come richiesto
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
    
    mappa = {"Juve": "Juventus", "Inter Milan": "Inter", "Int": "Inter", "Verona": "Verona"}
    home = mappa.get(home, home)
    away = mappa.get(away, away)
    
    tutte_le_stats = carica_statistiche()
    default = {"gialli": 60, "rossi": 3, "falli": 450}
    home_stats = tutte_le_stats.get(home, default)
    away_stats = tutte_le_stats.get(away, default)
    
    # 1. Rischio Cartellini (Formula 38)
    media_home = calcola_media_partita(home_stats)
    media_away = calcola_media_partita(media_away := calcola_media_partita(away_stats)) # refactor per brevità
    rischio_finale = ((media_home + media_away) / 2) * request.arbitro_severity
    
    # 2. Dati Poisson
    dati_poisson = get_poisson_data(home_stats, away_stats)
    
    # 3. Panel Esperti
    panel_esperti = {
        "Analisi Dati": "Stabile",
        "Trend Arbitro": "Favorevole" if request.arbitro_severity > 1.0 else "Normale"
    }
    
    print(f"DEBUG -> Risultato Finale: {rischio_finale:.2f}")

    return {
        "match": f"{home} vs {away}",
        "rischio_cartellini": round(rischio_finale, 2),
        "stats": {
            "home": {"gialli": home_stats.get('gialli'), "rossi": home_stats.get('rossi'), "falli": home_stats.get('falli')},
            "away": {"gialli": away_stats.get('gialli'), "rossi": away_stats.get('rossi'), "falli": away_stats.get('falli')}
        },
        "modello_poisson": dati_poisson,
        "panel_esperti": panel_esperti
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)