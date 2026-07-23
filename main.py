import os
import math
import requests
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# ==========================================
# 🌤️ CONFIGURAZIONE METEO (OPENWEATHERMAP)
# ==========================================
OPENWEATHER_API_KEY = "1276c6c958e9fa1f6d99da6fadb02421"

def ottieni_meteo_live(lat: float, lon: float) -> str:
    if not lat or not lon:
        return "Non disponibile"
        
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=it"
    
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            condizione = data["weather"][0]["description"].capitalize()
            temperatura = round(data["main"]["temp"])
            return f"{condizione}, {temperatura}°C"
        else:
            return "Errore meteo"
    except Exception:
        return "Servizio meteo irraggiungibile"

# ==========================================
# 🔌 MODULI ESTERNI (PLUG & PLAY)
# ==========================================
try:
    from expert_handler import get_expert_predictions
except ImportError:
    def get_expert_predictions(match_id):
        return {"status": "warning", "message": "Modulo esperti temporaneamente non disponibile", "data": []}

# ==========================================
# 🗄️ DATABASE PROPRIETARI (STADI, ALLENATORI & STATS LAMBDA)
# ==========================================
DB_STADI = {
    "Inter": {"nome": "Stadio Giuseppe Meazza", "terreno": "Erba Mista", "copertura": "Scoperto", "lat": 45.4781, "lon": 9.1240},
    "Lazio": {"nome": "Stadio Olimpico di Roma", "terreno": "Erba Naturale", "copertura": "Scoperto", "lat": 41.9339, "lon": 12.4547},
    "Milan": {"nome": "Stadio Giuseppe Meazza", "terreno": "Erba Mista", "copertura": "Scoperto", "lat": 45.4781, "lon": 9.1240},
    "Juventus": {"nome": "Allianz Stadium", "terreno": "Erba Naturale", "copertura": "Coperto", "lat": 45.1095, "lon": 7.6413},
    "Napoli": {"nome": "Stadio Diego Armando Maradona", "terreno": "Erba Naturale", "copertura": "Scoperto", "lat": 40.8279, "lon": 14.1931},
    "Roma": {"nome": "Stadio Olimpico di Roma", "terreno": "Erba Naturale", "copertura": "Scoperto", "lat": 41.9339, "lon": 12.4547},
    "Atalanta": {"nome": "Gewiss Stadium", "terreno": "Erba Naturale", "copertura": "Coperto", "lat": 45.7082, "lon": 9.6806},
    "Fiorentina": {"nome": "Stadio Artemio Franchi", "terreno": "Erba Naturale", "copertura": "Scoperto", "lat": 43.7808, "lon": 11.2822},
    "default": {"nome": "Stadio Ufficiale", "terreno": "Erba Naturale", "copertura": "Scoperto", "lat": 41.9028, "lon": 12.4964}
}

DB_ALLENATORI = {
    "Inter": {"nome": "Simone Inzaghi", "indice": "8.5"},
    "Lazio": {"nome": "Marco Baroni", "indice": "7.2"},
    "Milan": {"nome": "Paulo Fonseca", "indice": "7.0"},
    "Juventus": {"nome": "Thiago Motta", "indice": "7.8"},
    "Napoli": {"nome": "Antonio Conte", "indice": "8.8"},
    "Roma": {"nome": "Daniele De Rossi", "indice": "7.5"},
    "Atalanta": {"nome": "Gian Piero Gasperini", "indice": "8.6"},
    "default": {"nome": "Da aggiornare", "indice": "N/D"}
}

# 📊 NUOVO: MEDIA GOL ATTESI PER SQUADRA (CASA vs TRASFERTA)
DB_LAMBDA_SQUADRE = {
    "Inter": {"lambda_casa": 2.10, "lambda_ospite": 1.75},
    "Milan": {"lambda_casa": 1.80, "lambda_ospite": 1.40},
    "Juventus": {"lambda_casa": 1.65, "lambda_ospite": 1.20},
    "Napoli": {"lambda_casa": 1.85, "lambda_ospite": 1.45},
    "Roma": {"lambda_casa": 1.70, "lambda_ospite": 1.25},
    "Lazio": {"lambda_casa": 1.55, "lambda_ospite": 1.15},
    "Atalanta": {"lambda_casa": 2.00, "lambda_ospite": 1.60},
    "Fiorentina": {"lambda_casa": 1.50, "lambda_ospite": 1.10},
    "Bologna": {"lambda_casa": 1.45, "lambda_ospite": 1.05},
    "Torino": {"lambda_casa": 1.25, "lambda_ospite": 0.90},
    "Verona": {"lambda_casa": 1.10, "lambda_ospite": 0.85},
    "Udinese": {"lambda_casa": 1.20, "lambda_ospite": 0.95},
    "Genoa": {"lambda_casa": 1.15, "lambda_ospite": 0.85},
    "Monza": {"lambda_casa": 1.10, "lambda_ospite": 0.80},
    "Cagliari": {"lambda_casa": 1.15, "lambda_ospite": 0.75},
    "Empoli": {"lambda_casa": 1.00, "lambda_ospite": 0.70},
    "Lecce": {"lambda_casa": 1.05, "lambda_ospite": 0.70},
    "Parma": {"lambda_casa": 1.20, "lambda_ospite": 0.90},
    "Como": {"lambda_casa": 1.10, "lambda_ospite": 0.85},
    "Venezia": {"lambda_casa": 1.00, "lambda_ospite": 0.75},
    "default": {"lambda_casa": 1.35, "lambda_ospite": 1.00}
}

# ==========================================
# ⚖️ ANAGRAFICA DINAMICA SEVERITÀ ARBITRI
# ==========================================
DB_SEVERITA_ARBITRI = {
    "Daniele Orsato": "Alta (7.8)",
    "Marco Guida": "Media (6.5)",
    "Daniele Doveri": "Bassa (5.2)",
    "Fabio Maresca": "Alta (8.1)",
    "Davide Massa": "Media (6.8)",
    "Michael Fabbri": "Media (6.0)",
    "default": "Media (5.0)"
}

def scrappa_arbitro_live(squadra_casa: str, squadra_ospite: str) -> str:
    return "Daniele Doveri"

def genera_contesto_match(casa: str, ospite: str):
    casa_clean = casa.strip().title()
    ospite_clean = ospite.strip().title()

    stadio_info = DB_STADI.get(casa_clean, DB_STADI.get("default"))
    all_casa = DB_ALLENATORI.get(casa_clean, DB_ALLENATORI.get("default"))
    all_ospite = DB_ALLENATORI.get(ospite_clean, DB_ALLENATORI.get("default"))
    
    arbitro_designato = scrappa_arbitro_live(casa_clean, ospite_clean)
    severita_arbitro = DB_SEVERITA_ARBITRI.get(arbitro_designato, DB_SEVERITA_ARBITRI.get("default"))
    
    meteo_live = ottieni_meteo_live(stadio_info.get("lat"), stadio_info.get("lon"))
    
    return {
        "Stadio Casa": stadio_info["nome"],
        "Terreno & Copertura": f"{stadio_info['terreno']} - {stadio_info['copertura']}",
        "Allenatore Casa": all_casa["nome"],
        "Indice Tattico Casa": str(all_casa["indice"]),
        "Allenatore Ospite": all_ospite["nome"],
        "Indice Tattico Ospite": str(all_ospite["indice"]),
        "Arbitro Designato": arbitro_designato,
        "Severità Arbitro": severita_arbitro,
        "Meteo Live": meteo_live
    }

# ==========================================
# 🚀 INIZIALIZZAZIONE FASTAPI
# ==========================================
app = FastAPI(
    title="Schizzo Analytics Engine",
    description="Backend analitico con motore Poisson dinamico e architettura modulare.",
    version="2.3.1"
)

# ==========================================
# 📐 MODELLI DI INPUT E OUTPUT (PYDANTIC)
# ==========================================
class MatchRequest(BaseModel):
    match_id: Optional[str] = None
    squadra_casa: Optional[str] = None
    squadra_ospite: Optional[str] = None
    home: Optional[str] = None
    away: Optional[str] = None
    lambda_casa: Optional[float] = None
    lambda_ospite: Optional[float] = None
    moltiplicatore_infortuni: Optional[float] = 1.0
    moltiplicatore_stadio: Optional[float] = 1.0
    moltiplicatore_arbitro: Optional[float] = 1.0

# ==========================================
# 🧮 CORE ENGINE: MOTORE DI POISSON
# ==========================================
def poisson_probability(k: int, lambd: float) -> float:
    if lambd <= 0:
        return 0.0
    return (math.pow(lambd, k) * math.exp(-lambd)) / math.factorial(k)

def calcola_matrice_risultati(l_casa: float, l_ospite: float, max_gol: int = 5):
    matrice = {}
    for i in range(max_gol + 1):
        for j in range(max_gol + 1):
            p_i = poisson_probability(i, l_casa)
            p_j = poisson_probability(j, l_ospite)
            matrice[f"{i}-{j}"] = p_i * p_j
    return matrice

def elabora_mercati_poisson(l_casa: float, l_ospite: float):
    matrice = calcola_matrice_risultati(l_casa, l_ospite)
    
    p_1 = sum(prob for score, prob in matrice.items() if int(score.split('-')[0]) > int(score.split('-')[1]))
    p_X = sum(prob for score, prob in matrice.items() if int(score.split('-')[0]) == int(score.split('-')[1]))
    p_2 = sum(prob for score, prob in matrice.items() if int(score.split('-')[0]) < int(score.split('-')[1]))
    
    p_gg = sum(prob for score, prob in matrice.items() if int(score.split('-')[0]) > 0 and int(score.split('-')[1]) > 0)
    p_ng = 1.0 - p_gg
    
    under_over = {}
    for soglia in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]:
        u_p = sum(prob for score, prob in matrice.items() if (int(score.split('-')[0]) + int(score.split('-')[1])) < soglia)
        under_over[f"Under {soglia}"] = round(u_p * 100, 2)
        under_over[f"Over {soglia}"] = round((1.0 - u_p) * 100, 2)
        
    p_mg_1_3 = sum(prob for score, prob in matrice.items() if 1 <= (int(score.split('-')[0]) + int(score.split('-')[1])) <= 3)
    
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
        "version": "2.3.1",
        "principio": "Costruire, non Sostituire"
    }

@app.post("/analizza")
@app.post("/predict")
def analizza_partita(req: MatchRequest):
    casa = req.squadra_casa or req.home or "Casa"
    ospite = req.squadra_ospite or req.away or "Trasferta"
    match_id = req.match_id or f"{casa.lower()}_{ospite.lower()}"

    casa_clean = casa.strip().title()
    ospite_clean = ospite.strip().title()

    # Recupera i lambda specifici della squadra se non inviati manualmente
    stats_casa = DB_LAMBDA_SQUADRE.get(casa_clean, DB_LAMBDA_SQUADRE["default"])
    stats_ospite = DB_LAMBDA_SQUADRE.get(ospite_clean, DB_LAMBDA_SQUADRE["default"])

    l_casa_base = req.lambda_casa if req.lambda_casa is not None else stats_casa["lambda_casa"]
    l_ospite_base = req.lambda_ospite if req.lambda_ospite is not None else stats_ospite["lambda_ospite"]

    l_casa_adj = l_casa_base * req.moltiplicatore_infortuni * req.moltiplicatore_stadio
    l_ospite_adj = l_ospite_base * req.moltiplicatore_arbitro
    
    risultati_poisson = elabora_mercati_poisson(l_casa_adj, l_ospite_adj)
    contesto_match = genera_contesto_match(casa=casa, ospite=ospite)
    
    dati_esperti = []
    if match_id:
        res_esperti = get_expert_predictions(match_id)
        if res_esperti.get("status") == "success":
            dati_esperti = res_esperti.get("data", [])

    return {
        "partita": f"{casa} vs {ospite}",
        "match_id": match_id,
        "parametri_applicati": {
            "lambda_casa_effettivo": round(l_casa_adj, 2),
            "lambda_ospite_effettivo": round(l_ospite_adj, 2)
        },
        "previsioni_poisson": risultati_poisson,
        "info_match": contesto_match, 
        "modulo_esperti": {
            "disponibile": len(dati_esperti) > 0,
            "totale_esperti": len(dati_esperti),
            "lista_esperti": dati_esperti
        },
        "whale_alert": {
            "attivo": False,
            "volume_effettivo": "€0",
            "volume_normale": "€0",
            "sbilanciamento": "Nessuno"
        }
    }

@app.get("/esperti/{match_id}")
def ottieni_esperti(match_id: str):
    return get_expert_predictions(match_id)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)