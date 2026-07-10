from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import json
import os

app = FastAPI(title="Schizzo Analytics Engine V4.0")

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

def calcola_whale_alert(home: str, away: str):
    try:
        if not os.path.exists('serie_a_dati.csv'):
            return None
        df = pd.read_csv('serie_a_dati.csv')
        match_data = df[(df['HomeTeam'] == home) & (df['AwayTeam'] == away)]
        if not match_data.empty:
            max_h = match_data['MaxH'].values[0]
            avg_h = match_data['AvgH'].values[0]
            max_a = match_data['MaxA'].values[0]
            avg_a = match_data['AvgA'].values[0]
            soglia_allarme = 0.15
            if (max_h - avg_h) >= soglia_allarme:
                return {"polarizzazione": home, "intensita": "Alta (Flusso su Casa)"}
            elif (max_a - avg_a) >= soglia_allarme:
                return {"polarizzazione": away, "intensita": "Alta (Flusso su Ospite)"}
    except Exception as e:
        print(f"Errore analisi balene: {e}")
    return None

def carica_statistiche():
    try:
        with open('statistiche_complete.json', 'r') as f:
            return json.load(f)
    except Exception:
        return {}

@app.get("/")
def read_root():
    return {"status": "Schizzo Analytics Engine V4.0 è online."}

@app.post("/predict")
def predict_match(request: MatchRequest):
    # Normalizzazione iniziale del testo
    home = request.home.strip().title()
    away = request.away.strip().title()
    
    # dizionario di traduzione per i soprannomi o abbreviazioni
    DIZIONARIO_SQUADRE = {
        "Juve": "Juventus",
        "Inter Milan": "Inter",
        "Int": "Inter",
        "Verona": "Hellas Verona"
    }
    
    # Se inserisci "Juve", il sistema lo converte automaticamente in "Juventus"
    home = DIZIONARIO_SQUADRE.get(home, home)
    away = DIZIONARIO_SQUADRE.get(away, away)
    
    tutte_le_stats = carica_statistiche()
    
    home_raw = tutte_le_stats.get(home, {"gialli": 0, "rossi": 0, "falli": 0})
    away_raw = tutte_le_stats.get(away, {"gialli": 0, "rossi": 0, "falli": 0})
    
    stats_match = {
        "home": {
            "gialli": f"{home_raw.get('gialli', 0)} (Rossi: {home_raw.get('rossi', 0)})",
            "falli": home_raw.get("falli", 0)
        },
        "away": {
            "gialli": f"{away_raw.get('gialli', 0)} (Rossi: {away_raw.get('rossi', 0)})",
            "falli": away_raw.get("falli", 0)
        }
    }
    
    allarme_balene = calcola_whale_alert(home, away)
    alerts = {}
    if allarme_balene:
         alerts["flussi_monetari"] = allarme_balene
         
    rischio_base = 1.7 * request.arbitro_severity
         
    return {
        "match": f"{home} vs {away}",
        "rischio_cartellini": round(rischio_base, 2),
        "probabilita_mercato_implicita": 0.526,
        "analisi_valore": "Allineato",
        "alert": alerts,
        "stats": stats_match,
        "status": "Analisi completata con successo"
    }