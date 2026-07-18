import requests
import json
import os
import time
from scraper import get_quote_flashscore

# Configurazione API Football per Infortuni
API_KEY = "688289e248msh6d676c8b4186f49p118e28jsn6dc17b41e502"
CACHE_FILE = "cache_infortuni.json"
URL = "https://api-football-v1.p.rapidapi.com/v3/injuries"
HEADERS = {
    "x-rapidapi-key": API_KEY,
    "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
}

def fetch_infortuni_lega():
    """
    Scarica (o legge dalla cache) tutti gli infortuni della Serie A.
    Mantiene la cache di 24h per non bruciare le chiamate API gratuite.
    """
    if os.path.exists(CACHE_FILE):
        if (time.time() - os.path.getmtime(CACHE_FILE)) < 86400:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)

    # Aggiornamento dati (Serie A - ID 135)
    leghe = {"135": "serie_a"} 
    dati_raccolti = {}

    for id_lega, nome in leghe.items():
        response = requests.get(URL, headers=HEADERS, params={"league": id_lega, "season": "2026"})
        if response.status_code == 200:
            dati_raccolti[nome] = response.json().get("response", [])

    # Salva su file
    with open(CACHE_FILE, 'w') as f:
        json.dump(dati_raccolti, f)
    
    return dati_raccolti

def get_infortuni_live(home, away):
    """
    Filtra gli infortuni SOLO per le due squadre in campo,
    estraendoli dal dataset aggiornato della lega.
    """
    print(f"Recupero infortuni mirato per: {home} vs {away}")
    
    tutti_infortuni = fetch_infortuni_lega()
    infortuni_serie_a = tutti_infortuni.get("serie_a", [])
    
    # Struttura dati isolata per le due squadre
    infortuni_match = {
        home: {"giocatori_out": 0, "dettagli": []},
        away: {"giocatori_out": 0, "dettagli": []}
    }
    
    # Filtra solo quelli delle squadre del match (confronto stringhe sicuro)
    for infortunio in infortuni_serie_a:
        squadra_infortunio = infortunio.get("team", {}).get("name", "")
        giocatore = infortunio.get("player", {}).get("name", "")
        
        if home.lower() in squadra_infortunio.lower():
            infortuni_match[home]["giocatori_out"] += 1
            infortuni_match[home]["dettagli"].append(giocatore)
        elif away.lower() in squadra_infortunio.lower():
            infortuni_match[away]["giocatori_out"] += 1
            infortuni_match[away]["dettagli"].append(giocatore)
            
    return infortuni_match

def get_meteo_match(match_id):
    """
    Recupera le condizioni meteo per la partita. 
    Serve per attivare eventuali penalità in weights.py.
    """
    # Predisposto per la futura API meteo. Per ora è neutro.
    return "normale"

def get_dati_dinamici(home, away, match_id):
    """
    ORCHESTRATORE DINAMICO.
    Raccoglie tutti e soli i dati freschi necessari al calcolo matematico (Poisson).
    NESSUN COLLEGAMENTO CON IL DATABASE ESPERTI.
    """
    print(f"Avvio raccolta dati dinamici per Match ID: {match_id}")
    
    quota_live = get_quote_flashscore(match_id)
    
    dati_freschi = {
        "quote": quota_live,
        "infortuni": get_infortuni_live(home, away),
        "meteo": get_meteo_match(match_id),
        "squadra_aggressiva": False # Predisposto per l'integrazione falli/cartellini
    }
    
    print("Sistema Schizzo: Dati dinamici raccolti con successo.")
    return dati_freschi

if __name__ == "__main__":
    # Test diretto del file
    print("--- TEST HELPER DINAMICO API ---")
    # Usa due nomi veri della Serie A per testare il filtro
    risultato = get_dati_dinamici("Juventus", "Milan", "test-123")
    print(json.dumps(risultato, indent=4))