from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import json
import os
import math

app = FastAPI(title="Schizzo Analytics Engine V5.0 - Poisson Edition")

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

def poisson_probability(k, lambd):
    """Calcola la probabilità di segnare 'k' gol con una media attesa 'lambd'"""
    return (lambd**k * math.exp(-lambd)) / math.factorial(k)

def calcola_pronostico_poisson(home: str, away: str):
    """Genera le percentuali 1X2, Under/Over, Gol/NoGol e Risultati esatti"""
    try:
        if not os.path.exists('serie_a_dati.csv'):
            return None
            
        df = pd.read_csv('serie_a_dati.csv')
        
        # 1. Medie globali del campionato
        media_gol_casa = df['FTHG'].mean()
        media_gol_trasferta = df['FTAG'].mean()
        
        # 2. Statistiche Casa
        partite_casa = df[df['HomeTeam'] == home]
        if partite_casa.empty:
            return None
        gol_fatti_casa = partite_casa['FTHG'].mean()
        gol_subiti_casa = partite_casa['FTAG'].mean()
        
        # 3. Statistiche Trasferta
        partite_trasferta = df[df['AwayTeam'] == away]
        if partite_trasferta.empty:
            return None
        gol_fatti_trasferta = partite_trasferta['FTAG'].mean()
        gol_subiti_trasferta = partite_trasferta['FTHG'].mean()
        
        # 4. Calcolo Forze (Attacco/Difesa)
        forza_attacco_home = gol_fatti_casa / media_gol_casa
        forza_difesa_home = gol_subiti_casa / media_gol_trasferta
        
        forza_attacco_away = gol_fatti_trasferta / media_gol_trasferta
        forza_difesa_away = gol_subiti_trasferta / media_gol_casa
        
        # 5. Expected Goals (xG)
        xg_home = forza_attacco_home * forza_difesa_away * media_gol_casa
        xg_away = forza_attacco_away * forza_difesa_home * media_gol_trasferta
        
        # 6. Generazione matrice probabilità (fino a 5 gol a testa)
        prob_1 = prob_x = prob_2 = 0
        prob_over = prob_under = 0
        prob_gol = prob_nogol = 0
        risultati_esatti = {}

        for i in range(6): # Gol previsti Casa
            for j in range(6): # Gol previsti Trasferta
                prob = poisson_probability(i, xg_home) * poisson_probability(j, xg_away)
                
                # Calcolo 1X2
                if i > j: prob_1 += prob
                elif i == j: prob_x += prob
                else: prob_2 += prob
                
                # Calcolo Under/Over 2.5
                if (i + j) > 2.5: prob_over += prob
                else: prob_under += prob
                
                # Calcolo Gol/No Gol
                if i > 0 and j > 0: prob_gol += prob
                else: prob_nogol += prob
                
                # Mappatura risultato esatto
                risultati_esatti[f"{i}-{j}"] = prob
                
        # Estraiamo i 3 risultati più probabili
        top_3_risultati = sorted(risultati_esatti.items(), key=lambda x: x[1], reverse=True)[:3]
        top_3_formattati = {ris: f"{round(p * 100, 1)}%" for ris, p in top_3_risultati}

        return {
            "mercato_1X2": {"1": f"{round(prob_1*100, 1)}%", "X": f"{round(prob_x*100, 1)}%", "2": f"{round(prob_2*100, 1)}%"},
            "under_over": {"Under 2.5": f"{round(prob_under*100, 1)}%", "Over 2.5": f"{round(prob_over*100, 1)}%"},
            "gol_nogol": {"Gol": f"{round(prob_gol*100, 1)}%", "No Gol": f"{round(prob_nogol*100, 1)}%"},
            "risultati_esatti": top_3_formattati,
            "xG": {"home": round(xg_home, 2), "away": round(xg_away, 2)}
        }
    except Exception as e:
        print(f"Errore Poisson: {e}")
        return None

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
        pass
    return None

def carica_statistiche():
    try:
        with open('statistiche_complete.json', 'r') as f:
            return json.load(f)
    except Exception:
        return {}

@app.get("/")
def read_root():
    return {"status": "Schizzo Analytics Engine V5.0 è online."}

@app.post("/predict")
def predict_match(request: MatchRequest):
    home = request.home.strip().title()
    away = request.away.strip().title()
    
    DIZIONARIO_SQUADRE = {
        "Juve": "Juventus",
        "Inter Milan": "Inter",
        "Int": "Inter",
        "Verona": "Hellas Verona"
    }
    
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
    
    # NOVITÀ: Eseguiamo l'algoritmo predittivo
    modello_predittivo = calcola_pronostico_poisson(home, away)
         
    return {
        "match": f"{home} vs {away}",
        "rischio_cartellini": round(rischio_base, 2),
        "modello_poisson": modello_predittivo, # Rimpiazzato il dato provvisorio con le probabilità reali
        "alert": alerts,
        "stats": stats_match,
        "status": "Analisi completata con successo"
    }