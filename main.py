# main.py
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
    version="3.0.0"
)

@app.get("/")
def read_root():
    return {"status": "online", "app": "Schizzo Analytics Engine", "version": "3.0.0"}

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
    
    mercati = elabora_mercati_poisson(l_casa_adj, l_ospite_adj)
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