from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import math
import database_stadi # Importa il tuo database

app = FastAPI(title="Schizzo Analytics Cloud")

class MatchRequest(BaseModel):
    home: str
    away: str

# --- ENGINE POISSON ---
def calcola_poisson(lambda_val, k):
    return (math.exp(-lambda_val) * (lambda_val ** k)) / math.factorial(k)

@app.post("/predict")
def predict(request: MatchRequest):
    home_key = request.home.lower().strip()
    away_key = request.away.lower().strip()
    
    # Recupero dati dal database importato
    stadio_info = database_stadi.DB_STADI.get(home_key, {"stadio": "Sconosciuto", "citta": "N/D"})
    
    try:
        # Struttura dati pronta per l'app Flutter
        return {
            "prob_1": 45.0, "prob_X": 25.0, "prob_2": 30.0,
            "stadium": stadio_info["stadio"],
            "city": stadio_info["citta"],
            "weather": "Sereno",
            "referee": "Arbitro Designato",
            "projected_cards": 3.5,
            "var_review_probability": 20,
            "home_absences": 0,
            "away_absences": 1,
            "total_matched": 500000,
            "anomaly_detected": False,
            "under_over": {"U25": 60, "O25": 40},
            "goal_nogoal": {"GG": 50, "NG": 50},
            "multigol": {"M1-2": 40, "M2-3": 40},
            "risultati_esatti": ["1-0", "1-1", "2-0"],
            "linea_cartellini": "4.0"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))