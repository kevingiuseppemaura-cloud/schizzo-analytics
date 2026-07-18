import uvicorn
import sqlite3
import math
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import dell'orchestratore dinamico e del gestore pesi
from api_helper import get_dati_dinamici
from weights import get_context_multiplier

# Import dei database statici
try:
    from database_stadi import DB_STADI
except ImportError:
    DB_STADI = {}

try:
    from database_arbitri import DB_ARBITRI
except ImportError:
    DB_ARBITRI = {}

try:
    from database_allenatori import DB_ALLENATORI
except ImportError:
    DB_ALLENATORI = {}

# Inizializzazione dell'app FastAPI
app = FastAPI(title="Schizzo API - Motore Dinamico")

# Modello dati in ingresso dall'app Flutter
class MatchRequest(BaseModel):
    match_id: str
    home: str
    away: str

# ---------------------------------------------------------
# COMPARTO 1: MOTORE MATEMATICO (POISSON)
# ---------------------------------------------------------
def poisson_probability(k, lmbda):
    """Calcola la probabilità di fare 'k' gol dato un valore atteso 'lmbda'"""
    return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)

def calcola_poisson(dati_dinamici, config_statica, moltiplicatore):
    """
    Motore matematico basato su distribuzione di Poisson.
    Calcola le probabilità su una matrice di risultati esatti (0-5 gol).
    """
    # 1. Definizione Expected Goals (xG) base
    xg_home_base = 1.5 
    xg_away_base = 1.1 
    
    # 2. Applicazione del moltiplicatore dinamico
    xg_home = xg_home_base * moltiplicatore
    xg_away = xg_away_base / (moltiplicatore if moltiplicatore > 0 else 1)
    
    # 3. Calcolo matrice esatta
    max_gol = 5
    prob_1, prob_x, prob_2 = 0.0, 0.0, 0.0
    prob_over, prob_under, prob_gol, prob_nogol = 0.0, 0.0, 0.0, 0.0
    
    for h in range(max_gol + 1):
        for a in range(max_gol + 1):
            prob_match = poisson_probability(h, xg_home) * poisson_probability(a, xg_away)
            
            if h > a: prob_1 += prob_match
            elif h == a: prob_x += prob_match
            else: prob_2 += prob_match
                
            if (h + a) > 2: prob_over += prob_match
            else: prob_under += prob_match
                
            if h > 0 and a > 0: prob_gol += prob_match
            else: prob_nogol += prob_match

    totale = prob_1 + prob_x + prob_2
    
    return {
        "1": f"{round((prob_1 / totale) * 100, 1)}%",
        "X": f"{round((prob_x / totale) * 100, 1)}%",
        "2": f"{round((prob_2 / totale) * 100, 1)}%",
        "Over 2.5": f"{round((prob_over / totale) * 100, 1)}%",
        "Under 2.5": f"{round((prob_under / totale) * 100, 1)}%",
        "Gol": f"{round((prob_gol / totale) * 100, 1)}%",
        "NoGol": f"{round((prob_nogol / totale) * 100, 1)}%"
    }

@app.post("/predict")
async def get_prediction(request: MatchRequest):
    try:
        dati_dinamici = get_dati_dinamici(request.home, request.away, request.match_id)
        
        config_statica = {
            "stadio": DB_STADI.get(request.home, {}),
            "arbitro": DB_ARBITRI.get(request.match_id, {})
        }
        
        contesto_match = {
            "stadio_tipo": config_statica["stadio"].get("tipo_prato", "naturale"),
            "giocatori_chiave_out": dati_dinamici["infortuni"][request.home].get("giocatori_out", 0) > 2 or \
                                    dati_dinamici["infortuni"][request.away].get("giocatori_out", 0) > 2,
            "arbitro_severo": config_statica["arbitro"].get("severo", False)
        }
        
        moltiplicatore = get_context_multiplier(contesto_match)
        risultato = calcola_poisson(dati_dinamici, config_statica, moltiplicatore)
        
        return {"risultato": risultato}

    except Exception as e:
        print(f"Errore: {e}")
        raise HTTPException(status_code=500, detail="Errore elaborazione Schizzo")

# ---------------------------------------------------------
# COMPARTO 2: PANEL ESPERTI
# ---------------------------------------------------------
@app.get("/esperti/{match_id}")
async def get_esperti(match_id: str):
    try:
        conn = sqlite3.connect('esperti.db')
        cursor = conn.cursor()
        cursor.execute('SELECT fonte, valore FROM pronostici WHERE match_id = ?', (match_id,))
        rows = cursor.fetchall()
        conn.close()
        
        risultati = {row[0]: row[1] for row in rows} if rows else {"msg": "Nessun esperto disponibile"}
        return {"match_id": match_id, "esperti": risultati}

    except Exception as e:
        return {"match_id": match_id, "esperti": {"errore": str(e)}}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)