from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import json
import os

app = FastAPI(title="Schizzo Analytics Engine V4.0")

# Configurazione CORS per permettere all'App Flutter di comunicare col server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modello dei dati in ingresso dall'App
class MatchRequest(BaseModel):
    home: str
    away: str
    match_id: str
    arbitro_severity: float = 1.0

def calcola_whale_alert(home: str, away: str):
    """
    Scansiona il file CSV per rilevare anomalie nei flussi monetari
    confrontando i picchi di quota massima con le medie di mercato.
    """
    try:
        if not os.path.exists('serie_a_dati.csv'):
            return None
            
        df = pd.read_csv('serie_a_dati.csv')
        
        # Cerchiamo lo storico recente di questo scontro
        match_data = df[(df['HomeTeam'] == home) & (df['AwayTeam'] == away)]
        
        if not match_data.empty:
            # Estraiamo le quote per la squadra in casa e in trasferta
            max_h = match_data['MaxH'].values[0]
            avg_h = match_data['AvgH'].values[0]
            max_a = match_data['MaxA'].values[0]
            avg_a = match_data['AvgA'].values[0]
            
            # Algoritmo Balene: scostamento tra quota massima e media
            soglia_allarme = 0.15
            
            if (max_h - avg_h) >= soglia_allarme:
                return {"polarizzazione": home, "intensita": "Alta (Flusso su Casa)"}
            elif (max_a - avg_a) >= soglia_allarme:
                return {"polarizzazione": away, "intensita": "Alta (Flusso su Ospite)"}
                
    except Exception as e:
        print(f"Errore durante l'analisi balene: {e}")
        
    return None

def carica_statistiche():
    """Carica i falli e i cartellini dal JSON generato dallo scraper."""
    try:
        with open('statistiche_complete.json', 'r') as f:
            return json.load(f)
    except Exception:
        return {}

@app.get("/")
def read_root():
    return {"status": "Schizzo Analytics Engine V4.0 è online e operativo."}

@app.post("/predict")
def predict_match(request: MatchRequest):
    home = request.home
    away = request.away
    
    # 1. Carica le statistiche dal JSON
    tutte_le_stats = carica_statistiche()
    stats_match = {
        "home": tutte_le_stats.get(home, {"gialli": 0, "rossi": 0, "falli": 0}),
        "away": tutte_le_stats.get(away, {"gialli": 0, "rossi": 0, "falli": 0})
    }
    
    # 2. Eseguiamo il radar balene
    allarme_balene = calcola_whale_alert(home, away)
    
    # 3. Costruiamo l'oggetto alert per l'App Flutter
    alerts = {}
    if allarme_balene:
         alerts["flussi_monetari"] = allarme_balene
         
    # Calcolo del rischio base moltiplicato per la severità dell'arbitro
    rischio_base = 1.7 * request.arbitro_severity
         
    # 4. La risposta completa che viene inviata al telefono
    return {
        "match": f"{home} vs {away}",
        "rischio_cartellini": round(rischio_base, 2),
        "probabilita_mercato_implicita": 0.526, # Valore provvisorio, lo sostituiremo col modello Poisson
        "analisi_valore": "Allineato",
        "alert": alerts,
        "stats": stats_match,
        "status": "Analisi completata con successo"
    }