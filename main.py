from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import database_stadi
from cachetools import TTLCache
import math

app = FastAPI(title="Schizzo Analytics Engine V3.2")
cache_partite = TTLCache(maxsize=100, ttl=60)

class MatchRequest(BaseModel):
    home: str
    away: str
    match_id: str = None

def poisson_prob(lmbda, k):
    return (lmbda**k * math.exp(-lmbda)) / math.factorial(k)

def calcola_tutti_mercati(home_xg, away_xg):
    # Matrice risultati esatti (0-0 fino a 3-3)
    matrix = [[poisson_prob(home_xg, i) * poisson_prob(away_xg, j) for j in range(4)] for i in range(4)]
    
    home_win = sum(matrix[i][j] for i in range(4) for j in range(4) if i > j)
    draw = sum(matrix[i][i] for i in range(4))
    away_win = sum(matrix[i][j] for i in range(4) for j in range(4) if i < j)
    
    over_2_5 = sum(matrix[i][j] for i in range(4) for j in range(4) if i + j > 2.5)
    gol = sum(matrix[i][j] for i in range(1, 4) for j in range(1, 4))
    
    return {
        "1x2": {"1": round(home_win*100, 1), "X": round(draw*100, 1), "2": round(away_win*100, 1)},
        "under_over": {"over_2_5": round(over_2_5*100, 1), "under_2_5": round((1-over_2_5)*100, 1)},
        "gol_nogol": {"gol": round(gol*100, 1), "nogol": round((1-gol)*100, 1)}
    }

@app.post("/predict")
def predict(request: MatchRequest):
    if not request.match_id:
        # Nota: Qui useresti la tua funzione di ricerca automatica
        raise HTTPException(status_code=400, detail="ID Match richiesto")
    
    if request.match_id in cache_partite:
        return cache_partite[request.match_id]
    
    # Simulazione calcolo xG basato su database_stadi
    home_key = request.home.lower().strip()
    info = database_stadi.DB_STADI.get(home_key, {"indice_coach": 5.0})
    
    # Logica semplificata per il calcolo dei gol attesi (xG)
    home_xg = info["indice_coach"] / 2
    away_xg = 1.8 # Valore base ospite
    
    mercati = calcola_tutti_mercati(home_xg, away_xg)
    
    risposta = {
        "match": f"{request.home} vs {request.away}",
        "projections": mercati,
        "status": "Motore Poisson Attivo"
    }
    
    cache_partite[request.match_id] = risposta
    return risposta