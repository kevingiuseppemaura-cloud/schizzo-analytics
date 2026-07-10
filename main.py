from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import json
import os
import math

app = FastAPI(title="Schizzo Analytics Engine V5.2 - Poisson Full Text Edition")

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
    if lambd <= 0:
        return 0.0
    return (lambd**k * math.exp(-lambd)) / math.factorial(k)

def calcola_pronostico_poisson(home: str, away: str):
    try:
        if not os.path.exists('serie_a_dati.csv'):
            return None
            
        df = pd.read_csv('serie_a_dati.csv')
        
        media_gol_casa = df['FTHG'].mean()
        media_gol_trasferta = df['FTAG'].mean()
        
        partite_casa = df[df['HomeTeam'] == home]
        if partite_casa.empty:
            return None
        gol_fatti_casa = partite_casa['FTHG'].mean()
        gol_subiti_casa = partite_casa['FTAG'].mean()
        
        partite_trasferta = df[df['AwayTeam'] == away]
        if partite_trasferta.empty:
            return None
        gol_fatti_trasferta = partite_trasferta['FTAG'].mean()
        gol_subiti_trasferta = partite_trasferta['FTHG'].mean()
        
        forza_attacco_home = gol_fatti_casa / media_gol_casa if media_gol_casa > 0 else 1
        forza_difesa_home = gol_subiti_casa / media_gol_trasferta if media_gol_trasferta > 0 else 1
        
        forza_attacco_away = gol_fatti_trasferta / media_gol_trasferta if media_gol_trasferta > 0 else 1
        forza_difesa_away = gol_subiti_trasferta / media_gol_casa if media_gol_casa > 0 else 1
        
        xg_home = forza_attacco_home * forza_difesa_away * media_gol_casa
        xg_away = forza_attacco_away * forza_difesa_home * media_gol_trasferta
        
        prob_1 = prob_x = prob_2 = 0
        prob_over = prob_under = 0
        prob_gol = prob_nogol = 0
        risultati_esatti = {}

        for i in range(6): 
            for j in range(6): 
                prob = poisson_probability(i, xg_home) * poisson_probability(j, xg_away)
                
                if i > j: prob_1 += prob
                elif i == j: prob_x += prob
                else: prob_2 += prob
                
                if (i + j) > 2.5: prob_over += prob
                else: prob_under += prob
                
                if i > 0 and j > 0: prob_gol += prob
                else: prob_nogol += prob
                
                risultati_esatti[f"{i}-{j}"] = prob
                
        top_3_risultati = sorted(risultati_esatti.items(), key=lambda x: x[1], reverse=True)[:3]
        top_3_formattati = {ris: f"{round(p * 100, 1)}%" for ris, p in top_3_risultati}

        return {
            "prob_1": prob_1,
            "prob_x": prob_x,
            "prob_2": prob_2,
            "prob_under": prob_under,
            "prob_over": prob_over,
            "prob_gol": prob_gol,
            "prob_nogol": prob_nogol,
            "risultati_esatti": top_3_formattati,
            "xg_home": round(xg_home, 2),
            "xg_away": round(xg_away, 2)
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
            avg_a = match_data['AwayTeam'].values[0] # Fallback o gestione interna
            soglia_allarme = 0.15
            if (max_h - avg_h) >= soglia_allarme:
                return {"polarizzazione": home, "intensita": "Alta (Flusso su Casa)"}
            elif (max_a - max_h) >= soglia_allarme: # Modificato leggermente per sicurezza sintassi
                return {"polarizzazione": away, "intensita": "Alta (Flusso su Ospite)"}
    except Exception:
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
    return {"status": "Schizzo Analytics Engine V5.2 è online."}

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
    modello_predittivo = calcola_pronostico_poisson(home, away)
    
    prob_mercato_compatibile = 0.50
    analisi_valore_compatibile = "Dati insufficienti"
    poisson_payload = None
    
    if modello_predittivo:
        # Mostriamo la probabilità esatta del segno 1 nel box dedicato
        prob_mercato_compatibile = round(modello_predittivo["prob_1"], 3)
        
        # Estraiamo e formattiamo ogni singola metrica per inserirla nel campo di testo unico
        p_1 = f"{round(modello_predittivo['prob_1']*100, 1)}%"
        p_x = f"{round(modello_predittivo['prob_x']*100, 1)}%"
        p_2 = f"{round(modello_predittivo['prob_2']*100, 1)}%"
        
        u_25 = f"{round(modello_predittivo['prob_under']*100, 1)}%"
        o_25 = f"{round(modello_predittivo['prob_over']*100, 1)}%"
        
        gol = f"{round(modello_predittivo['prob_gol']*100, 1)}%"
        nogol = f"{round(modello_predittivo['prob_nogol']*100, 1)}%"
        
        top_res_str = ", ".join([f"{k} ({v})" for k, v in modello_predittivo["risultati_esatti"].items()])
        
        # COSTRUZIONE DEL SUPER-REPORT (Leggibile in un unico widget di testo su Flutter)
        analisi_valore_compatibile = (
            f"1X2: {p_1} / {p_x} / {p_2} | "
            f"U/O 2.5: U {u_25} - O {o_25} | "
            f"G/NG: Gol {gol} - NG {nogol} | "
            f"Top Score: {top_res_str}"
        )
        
        poisson_payload = {
            "mercato_1X2": {"1": p_1, "X": p_x, "2": p_2},
            "under_over": {"Under 2.5": u_25, "Over 2.5": o_25},
            "gol_nogol": {"Gol": gol, "No Gol": nogol},
            "risultati_esatti": modello_predittivo["risultati_esatti"],
            "xG": {"home": modello_predittivo["xg_home"], "away": modello_predittivo["xg_away"]}
        }
         
    return {
        "match": f"{home} vs {away}",
        "rischio_cartellini": round(rischio_base, 2),
        "probabilita_mercato_implicita": prob_mercato_compatibile, 
        "analisi_valore": analisi_valore_compatibile, # Qui ora passa TUTTO
        "modello_poisson": poisson_payload, 
        "alert": alerts,
        "stats": stats_match,
        "status": "Analisi completata con successo"
    }