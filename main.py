import os
import math
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# ==========================================
# 🔌 MODULI ESTERNI (PLUG & PLAY)
# ==========================================
# In conformità con il principio "Costruire, non Sostituire":
# Importiamo il modulo esperti in maniera isolata e protetta.
try:
    from expert_handler import get_expert_predictions
except ImportError:
    # Fallback di sicurezza: se il modulo è assente, il core backend non crasha.
    def get_expert_predictions(match_id):
        return {"status": "warning", "message": "Modulo esperti temporaneamente non disponibile", "data": []}


# ==========================================
# 🚀 INIZIALIZZAZIONE FASTAPI
# ==========================================
app = FastAPI(
    title="Schizzo Analytics Engine",
    description="Backend analitico con motore Poisson dinamico e architettura modulare.",
    version="2.0.0"
)


# ==========================================
# 📐 MODELLI DI INPUT E OUTPUT (PYDANTIC)
# ==========================================
class MatchRequest(BaseModel):
    match_id: Optional[str] = None
    squadra_casa: str
    squadra_ospite: str
    lambda_casa: float = 1.45  # Valore atteso gol casa
    lambda_ospite: float = 1.10 # Valore atteso gol ospite
    moltiplicatore_infortuni: Optional[float] = 1.0
    moltiplicatore_stadio: Optional[float] = 1.0
    moltiplicatore_arbitro: Optional[float] = 1.0


# ==========================================
# 🧮 CORE ENGINE: MOTORE DI POISSON (INALTERATO)
# ==========================================
def poisson_probability(k: int, lambd: float) -> float:
    """Calcola la probabilità di Poisson per k eventi con valore atteso lambda."""
    if lambd <= 0:
        return 0.0
    return (math.pow(lambd, k) * math.exp(-lambd)) / math.factorial(k)

def calcola_matrice_risultati(l_casa: float, l_ospite: float, max_gol: int = 5):
    """Calcola la matrice di probabilità dei risultati esatti fino a max_gol."""
    matrice = {}
    for i in range(max_gol + 1):
        for j in range(max_gol + 1):
            p_i = poisson_probability(i, l_casa)
            p_j = poisson_probability(j, l_ospite)
            matrice[f"{i}-{j}"] = p_i * p_j
    return matrice

def elabora_mercati_poisson(l_casa: float, l_ospite: float):
    """Elabora i mercati supportati (1X2, U/O, Gol/NoGol, Multigol, Risultati Esatti)."""
    matrice = calcola_matrice_risultati(l_casa, l_ospite)
    
    p_1 = sum(prob for score, prob in matrice.items() if int(score.split('-')[0]) > int(score.split('-')[1]))
    p_X = sum(prob for score, prob in matrice.items() if int(score.split('-')[0]) == int(score.split('-')[1]))
    p_2 = sum(prob for score, prob in matrice.items() if int(score.split('-')[0]) < int(score.split('-')[1]))
    
    p_gg = sum(prob for score, prob in matrice.items() if int(score.split('-')[0]) > 0 and int(score.split('-')[1]) > 0)
    p_ng = 1.0 - p_gg
    
    # Under / Over (0.5 - 5.5)
    under_over = {}
    for soglia in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]:
        u_p = sum(prob for score, prob in matrice.items() if (int(score.split('-')[0]) + int(score.split('-')[1])) < soglia)
        under_over[f"Under {soglia}"] = round(u_p * 100, 2)
        under_over[f"Over {soglia}"] = round((1.0 - u_p) * 100, 2)
        
    # Multigol 1-3
    p_mg_1_3 = sum(prob for score, prob in matrice.items() if 1 <= (int(score.split('-')[0]) + int(score.split('-')[1])) <= 3)
    
    # Top 3 Risultati Esatti
    top_esatti = sorted(matrice.items(), key=lambda x: x[1], reverse=True)[:3]
    top_esatti_fmt = [{"risultato": k, "probabilita": round(v * 100, 2)} for k, v in top_esatti]

    return {
        "esito_1x2": {
            "1": round(p_1 * 100, 2),
            "X": round(p_X * 100, 2),
            "2": round(p_2 * 100, 2)
        },
        "gol_nogol": {
            "Gol": round(p_gg * 100, 2),
            "NoGol": round(p_ng * 100, 2)
        },
        "under_over": under_over,
        "multigol_1_3": round(p_mg_1_3 * 100, 2),
        "top_3_risultati_esatti": top_esatti_fmt
    }


# ==========================================
# 📡 ROTTE E ENDPOINT API
# ==========================================

@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "Schizzo Analytics Engine",
        "version": "2.0.0",
        "principio": "Costruire, non Sostituire"
    }


@app.post("/analizza")
def analizza_partita(req: MatchRequest):
    """
    Endpoint principale:
    1. Calcola l'analisi Poisson con i moltiplicatori di contesto.
    2. Interroga in sicurezza il modulo esperti (se match_id viene fornito).
    """
    # 1. Moltiplicatori contestuali
    l_casa_adj = req.lambda_casa * req.moltiplicatore_infortuni * req.moltiplicatore_stadio
    l_ospite_adj = req.lambda_ospite * req.moltiplicatore_arbitro
    
    # 2. Calcoli matematici core
    risultati_poisson = elabora_mercati_poisson(l_casa_adj, l_ospite_adj)
    
    # 3. Layer informativo additivo (Modulo esperti)
    dati_esperti = []
    if req.match_id:
        res_esperti = get_expert_predictions(req.match_id)
        if res_esperti.get("status") == "success":
            dati_esperti = res_esperti.get("data", [])

    # 4. Output completo e unificato
    return {
        "partita": f"{req.squadra_casa} vs {req.squadra_ospite}",
        "match_id": req.match_id,
        "parametri_applicati": {
            "lambda_casa_effettivo": round(l_casa_adj, 2),
            "lambda_ospite_effettivo": round(l_ospite_adj, 2)
        },
        "previsioni_poisson": risultati_poisson,
        "modulo_esperti": {
            "disponibile": len(dati_esperti) > 0,
            "totale_esperti": len(dati_esperti),
            "lista_esperti": dati_esperti
        }
    }


@app.get("/esperti/{match_id}")
def ottieni_esperti(match_id: str):
    """Endpoint autonomo per consultare direttamente gli esperti tramite il loro modulo."""
    return get_expert_predictions(match_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)