from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import os
import uvicorn

app = FastAPI(title="Schizzo Analytics Engine - Pure Data")

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

@app.post("/predict")
async def predict_match(request: MatchRequest):
    home = request.home.strip().title()
    away = request.away.strip().title()
    
    # Dizionario correzioni nomi
    mappa = {"Juve": "Juventus", "Inter Milan": "Inter", "Int": "Inter", "Verona": "Verona"}
    home = mappa.get(home, home)
    away = mappa.get(away, away)
    
    tutte_le_stats = carica_statistiche()
    
    # Valori di default realistici basati sulla media (solo se la squadra manca)
    default = {"gialli": 70, "rossi": 3, "falli": 450}
    home_stats = tutte_le_stats.get(home, default)
    away_stats = tutte_le_stats.get(away, default)
    
    # FORMULA PURA: (Gialli + (Rossi * 3)) / 38
    # Trasforma il totale in MEDIA PARTITA. Nessun numero arbitrario aggiunto.
    def calcola_media_partita(stats):
        g = float(stats.get('gialli', 0))
        r = float(stats.get('rossi', 0))
        return (g + (r * 3)) / 38

    media_home = calcola_media_partita(home_stats)
    media_away = calcola_media_partita(away_stats)
    
    # RISCHIO FINALE: Media delle medie * Severità Arbitro
    rischio_finale = ((media_home + media_away) / 2) * request.arbitro_severity
    
    print(f"DEBUG -> {home}: {media_home:.2f} | {away}: {media_away:.2f} | Arb: {request.arbitro_severity} | RISULTATO: {rischio_finale:.2f}")

    return {
        "match": f"{home} vs {away}",
        "rischio_cartellini": round(rischio_finale, 2),
        "stats": {
            "home": {"gialli": home_stats.get('gialli'), "falli": home_stats.get('falli')},
            "away": {"gialli": away_stats.get('gialli'), "falli": away_stats.get('falli')}
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)