from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import json
import os
import math
import esperti # Modulo integrato

app = FastAPI(title="Schizzo Analytics Engine V5.3 - Advanced Engine")

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
    default_response = {}
    try:
        if not os.path.exists('serie_a_dati.csv'):
            return default_response
            
        df = pd.read_csv('serie_a_dati.csv')
        df.columns = df.columns.str.strip()
        
        media_gol_casa = df['FTHG'].mean()
        media_gol_trasferta = df['FTAG'].mean()
        
        partite_casa = df[df['HomeTeam'] == home]
        if partite_casa.empty:
            return default_response
        
        gol_fatti_casa = partite_casa['FTHG'].mean()
        gol_subiti_casa = partite_casa['FTAG'].mean()
        
        partite_trasferta = df[df['AwayTeam'] == away]
        if partite_trasferta.empty:
            return default_response
            
        gol_fatti_trasferta = partite_trasferta['FTAG'].mean()
        gol_subiti_trasferta = partite_trasferta['FTHG'].mean()
        
        forza_attacco_home = gol_fatti_casa / media_gol_casa if media_gol_casa > 0 else 1
        forza_difesa_home = gol_subiti_casa / media_gol_trasferta if media_gol_trasferta > 0 else 1
        
        forza_attacco_away = gol_fatti_trasferta / media_gol_trasferta if media_gol_trasferta > 0 else 1
        forza_difesa_away = gol_subiti_trasferta / media_gol_casa if media_gol_casa > 0 else 1
        
        xg_home = forza_attacco_home * forza_difesa_away * media_gol_casa
        xg_away = forza_attacco_away * forza_difesa_home * media_gol_trasferta
        
        prob_1 = prob_x = prob_2 = 0
        prob_gol = prob_nogol = 0
        risultati_esatti = {}
        
        soglie_uo = [0.5, 1.5, 2.5, 3.5, 4.5]
        conteggio_uo = {soglia: {"under": 0.0, "over": 0.0} for soglia in soglie_uo}
        
        intervalli_multigol = {
            "1-2": (1, 2), "1-3": (1, 3), "1-4": (1, 4),
            "2-3": (2, 3), "2-4": (2, 4), "2-5": (2, 5), "3-4": (3, 4)
        }
        conteggio_multigol = {chiave: 0.0 for chiave in intervalli_multigol.keys()}

        for i in range(6): 
            for j in range(6): 
                prob = poisson_probability(i, xg_home) * poisson_probability(j, xg_away)
                totale_gol = i + j
                
                if i > j: prob_1 += prob
                elif i == j: prob_x += prob
                else: prob_2 += prob
                
                if i > 0 and j > 0: prob_gol += prob
                else: prob_nogol += prob
                
                for soglia in soglie_uo:
                    if totale_gol > soglia:
                        conteggio_uo[soglia]["over"] += prob
                    else:
                        conteggio_uo[soglia]["under"] += prob
                
                for chiave, (min_g, max_g) in intervalli_multigol.items():
                    if min_g <= totale_gol <= max_g:
                        conteggio_multigol[chiave] += prob
                
                risultati_esatti[f"{i}-{j}"] = prob
                
        top_3_risultati = sorted(risultati_esatti.items(), key=lambda x: x[1], reverse=True)[:3]

        payload_uo = {}
        for s in soglie_uo:
            payload_uo[f"U/O {s}"] = {
                "Under": f"{round(conteggio_uo[s]['under'] * 100, 1)}%",
                "Over": f"{round(conteggio_uo[s]['over'] * 100, 1)}%"
            }
            
        payload_mg = {f"Multigol {k}": f"{round(v * 100, 1)}%" for k, v in conteggio_multigol.items()}

        return {
            "mercato_1X2": {
                "1": f"{round(prob_1*100, 1)}%", 
                "X": f"{round(prob_x*100, 1)}%", 
                "2": f"{round(prob_2*100, 1)}%"
            },
            "gol_nogol": {
                "Gol": f"{round(prob_gol*100, 1)}%", 
                "No Gol": f"{round(prob_nogol*100, 1)}%"
            },
            "under_over_completo": payload_uo,
            "multigol_completo": payload_mg,
            "risultati_esatti": {ris: f"{round(p * 100, 1)}%" for ris, p in top_3_risultati},
            "xG": {"home": round(xg_home, 2), "away": round(xg_away, 2)}
        }
    except Exception as e:
        print(f"Errore Poisson: {e}")
        return default_response

def calcola_whale_alert(home: str, away: str):
    try:
        if not os.path.exists('serie_a_dati.csv'):
            return None
        df = pd.read_csv('serie_a_dati.csv')
        match_data = df[(df['HomeTeam'] == home) & (df['AwayTeam'] == away)]
        if not match_data.empty:
            max_h = match_data['MaxH'].values[0]
            avg_h = match_data['AvgH'].values[0]
            soglia_allarme = 0.15
            if (max_h - avg_h) >= soglia_allarme:
                return {"polarizzazione": home, "intensita": "Alta (Flusso su Casa)"}
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
    return {"status": "Schizzo Analytics Engine V5.3 è online."}

@app.post("/predict")
async def predict_match(request: MatchRequest):
    home = request.home.strip().title()
    away = request.away.strip().title()
    
    DIZIONARIO_SQUADRE = {"Juve": "Juventus", "Inter Milan": "Inter", "Int": "Inter", "Verona": "Hellas Verona"}
    home = DIZIONARIO_SQUADRE.get(home, home)
    away = DIZIONARIO_SQUADRE.get(away, away)
    
    tutte_le_stats = carica_statistiche()
    home_raw = tutte_le_stats.get(home, {"gialli": 0, "rossi": 0, "falli": 0})
    away_raw = tutte_le_stats.get(away, {"gialli": 0, "rossi": 0, "falli": 0})
    
    stats_match = {
        "home": {"gialli": f"{home_raw.get('gialli', 0)} (Rossi: {home_raw.get('rossi', 0)})", "falli": home_raw.get("falli", 0)},
        "away": {"gialli": f"{away_raw.get('gialli', 0)} (Rossi: {away_raw.get('rossi', 0)})", "falli": away_raw.get("falli", 0)}
    }
    
    allarme_balene = calcola_whale_alert(home, away)
    alerts = {}
    if allarme_balene: alerts["flussi_monetari"] = allarme_balene
         
    rischio_base = 1.7 * request.arbitro_severity
    modello_predittivo = calcola_pronostico_poisson(home, away)
    
    # Integrazione Panel Esperti
    panel_esperti = await esperti.get_tutti_esperti(request.match_id)
         
    return {
        "match": f"{home} vs {away}",
        "rischio_cartellini": round(rischio_base, 2),
        "modello_poisson": modello_predittivo,
        "panel_esperti": panel_esperti,
        "alert": alerts,
        "stats": stats_match,
        "status": "Analisi completata"
    }