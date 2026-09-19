# main.py
import math
from fastapi import FastAPI
from database import DB_LAMBDA_SQUADRE
from schemas import MatchRequest
from services import (
    normalizza_nome_squadra, calcola_lambda_avanzato,
    elabora_mercati_poisson, genera_contesto_match,
    esegui_master_calculator, genera_parere_gemini
)

app = FastAPI(
    title="Schizzo Analytics Engine",
    description="Backend modulare e ottimizzato per pronostici calcistici.",
    version="3.1.0"
)

def poisson_prob(lmbda, k):
    if lmbda <= 0 and k == 0:
        return 1.0
    if lmbda <= 0:
        return 0.0
    return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)

def calcola_mercati_completi_poisson(l_casa, l_ospite):
    p_1 = 0.0
    p_x = 0.0
    p_2 = 0.0
    p_gol = 0.0
    
    uo_vals = {1.5: 0.0, 2.5: 0.0, 3.5: 0.0, 4.5: 0.0}
    multigol_vals = {"1-2": 0.0, "1-3": 0.0, "1-4": 0.0, "1-5": 0.0}
    risultati_raw = []

    for i in range(7):  # Gol casa da 0 a 6
        p_i = poisson_prob(l_casa, i)
        for j in range(7):  # Gol ospite da 0 a 6
            p_j = poisson_prob(l_ospite, j)
            p_ij = p_i * p_j
            tot_gol = i + j

            # Esito 1X2
            if i > j:
                p_1 += p_ij
            elif i == j:
                p_x += p_ij
            else:
                p_2 += p_ij

            # Gol / No Gol
            if i > 0 and j > 0:
                p_gol += p_ij

            # Under / Over
            for line in [1.5, 2.5, 3.5, 4.5]:
                if tot_gol < line:
                    uo_vals[line] += p_ij

            # Multigol
            if 1 <= tot_gol <= 2:
                multigol_vals["1-2"] += p_ij
            if 1 <= tot_gol <= 3:
                multigol_vals["1-3"] += p_ij
            if 1 <= tot_gol <= 4:
                multigol_vals["1-4"] += p_ij
            if 1 <= tot_gol <= 5:
                multigol_vals["1-5"] += p_ij

            risultati_raw.append({
                "risultato": f"{i}-{j}",
                "prob": p_ij
            })

    def quota_da_prob(p):
        if p <= 0:
            return 0.0
        return round(100.0 / p, 2)

    # Normalizzazione 1X2
    total_1x2 = p_1 + p_x + p_2
    if total_1x2 > 0:
        p_1_pct = (p_1 / total_1x2) * 100.0
        p_x_pct = (p_x / total_1x2) * 100.0
        p_2_pct = (p_2 / total_1x2) * 100.0
    else:
        p_1_pct, p_x_pct, p_2_pct = 33.3, 33.3, 33.3

    esito_1x2 = {
        "1": {"probabilita": round(p_1_pct, 1), "quota": quota_da_prob(p_1_pct)},
        "X": {"probabilita": round(p_x_pct, 1), "quota": quota_da_prob(p_x_pct)},
        "2": {"probabilita": round(p_2_pct, 1), "quota": quota_da_prob(p_2_pct)},
    }

    # Gol / No Gol
    p_gol_pct = p_gol * 100.0
    p_nogol_pct = (1.0 - p_gol) * 100.0
    gol_no_gol = {
        "Gol": {"probabilita": round(p_gol_pct, 1), "quota": quota_da_prob(p_gol_pct)},
        "No Gol": {"probabilita": round(p_nogol_pct, 1), "quota": quota_da_prob(p_nogol_pct)},
    }

    # Under / Over
    under_over_final = {}
    for line in [1.5, 2.5, 3.5, 4.5]:
        u_prob = uo_vals[line] * 100.0
        o_prob = (1.0 - uo_vals[line]) * 100.0
        under_over_final[f"Under {line}"] = {"probabilita": round(u_prob, 1), "quota": quota_da_prob(u_prob)}
        under_over_final[f"Over {line}"] = {"probabilita": round(o_prob, 1), "quota": quota_da_prob(o_prob)}

    # Multigol
    multigol_final = {}
    for mg_key, val in multigol_vals.items():
        prob_pct = val * 100.0
        multigol_final[mg_key] = {"probabilita": round(prob_pct, 1), "quota": quota_da_prob(prob_pct)}

    # Top 3 Risultati Esatti
    risultati_raw.sort(key=lambda x: x["prob"], reverse=True)
    top_3 = []
    for r in risultati_raw[:3]:
        prob_pct = r["prob"] * 100.0
        top_3.append({
            "risultato": r["risultato"],
            "probabilita": round(prob_pct, 1),
            "quota": quota_da_prob(prob_pct)
        })

    return {
        "esito_1x2": esito_1x2,
        "gol_no_gol": gol_no_gol,
        "under_over": under_over_final,
        "multigol": multigol_final,
        "top_3_risultati_esatti": top_3
    }

@app.get("/")
def read_root():
    return {"status": "online", "app": "Schizzo Analytics Engine", "version": "3.1.0"}

@app.post("/api/calcola-match")
@app.post("/calcola-match")
@app.post("/analizza")
def calcola_match(req: MatchRequest):
    casa = req.squadra_casa or req.home or "Casa"
    ospite = req.squadra_ospite or req.away or "Trasferta"
    match_id = req.match_id or f"{casa.lower()}_{ospite.lower()}"

    casa_key = normalizza_nome_squadra(casa)
    ospite_key = normalizza_nome_squadra(ospite)

    stats_casa = DB_LAMBDA_SQUADRE.get(casa_key, DB_LAMBDA_SQUADRE["default"])
    stats_ospite = DB_LAMBDA_SQUADRE.get(ospite_key, DB_LAMBDA_SQUADRE["default"])

    l_casa_base = req.lambda_casa if req.lambda_casa is not None else stats_casa["lambda_casa"]
    l_ospite_base = req.lambda_ospite if req.lambda_ospite is not None else stats_ospite["lambda_ospite"]

    l_casa_adj, l_ospite_adj = calcola_lambda_avanzato(
        casa_key, ospite_key,
        l_casa_base, l_ospite_base,
        req.moltiplicatore_infortuni,
        req.moltiplicatore_stadio,
        req.moltiplicatore_arbitro
    )
    
    # Genera i mercati completi garantiti
    mercati = calcola_mercati_completi_poisson(l_casa_adj, l_ospite_adj)
    
    contesto_match = genera_contesto_match(casa=casa, ospite=ospite)
    master_stats = esegui_master_calculator(casa, ospite, contesto_match)

    try:
        parere_gemini = genera_parere_gemini(casa, ospite, contesto_match, mercati)
    except Exception as e:
        print(f"DEBUG - Errore critico in genera_parere_gemini: {str(e)}")
        parere_gemini = f"Errore tecnico Gemini: {str(e)}"

    intelligence = {
        'mister': f"Casa: {contesto_match.get('Allenatore Casa')} (Tattica {contesto_match.get('Indice Tattico Casa')}) | Ospite: {contesto_match.get('Allenatore Ospite')} (Tattica {contesto_match.get('Indice Tattico Ospite')})",
        'arbitro': f"{contesto_match.get('Arbitro Designato')} (Severità: {contesto_match.get('Severità Arbitro')})",
        'infortunati': "Rosa a disposizione ottimale",
        'stadium': f"{contesto_match.get('Stadio Casa')} ({contesto_match.get('Città')}) - Meteo: {contesto_match.get('Meteo Live')}",
        'flussi': master_stats['flussi_monetari']
    }

    return {
        "match": f"{casa} vs {ospite}",
        "match_id": match_id,
        "parametri_applicati": {
            "lambda_casa_effettivo": round(l_casa_adj, 2),
            "lambda_ospite_effettivo": round(l_ospite_adj, 2)
        },
        "poisson": mercati,
        "previsioni_poisson": mercati,
        "contesto": contesto_match,
        "info_match": contesto_match,
        "analisi_avanzata": master_stats,
        "master_calculator": master_stats,
        "intelligence": intelligence,
        "parere_gemini": parere_gemini,
        "panel_esperti": f"Analisi tattica: {master_stats['fattori_umani']}. Flussi: {master_stats['flussi_monetari']}."
    }