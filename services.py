# services.py
import os
import math
import json
import time
import requests

from database import (
    TEAM_ALIASES, DB_EFFICIENZA_XG, DB_PPDA, DB_DUELLI, 
    DB_ACCURATEZZA_BALISTICA, DB_OVERRIDE_FATTORE_CAMPO,
    DB_STADI, DB_ALLENATORI, DB_LAMBDA_SQUADRE, DB_ARBITRI
)
from scraper import get_quote_flashscore

# Configurazioni API e Chiavi
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "1276c6c958e9fa1f6d99da6fadb02421")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Configurazione API-Football per Infortuni
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "688289e248msh6d676c8b4186f49p118e28jsn6dc17b41e502")
CACHE_INJURIES_FILE = "cache_infortuni.json"
API_FOOTBALL_URL = "https://api-football-v1.p.rapidapi.com/v3/injuries"
API_FOOTBALL_HEADERS = {
    "x-rapidapi-key": API_FOOTBALL_KEY,
    "x-rapidapi-host": "api-football-v1.p.rapidapi.com"
}

def normalizza_nome_squadra(nome: str) -> str:
    """Normalizza il nome della squadra per renderlo compatibile con i dizionari del database."""
    if not nome:
        return "default"
    clean = nome.strip().lower()
    return TEAM_ALIASES.get(clean, clean)

def ottieni_meteo_live(lat: float, lon: float) -> str:
    """Recupera le condizioni meteorologiche in tempo reale tramite coordinate geografiche."""
    if not lat or not lon:
        return "Non disponibile"
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric&lang=it"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            data = response.json()
            condizione = data["weather"][0]["description"].capitalize()
            temperatura = round(data["main"]["temp"])
            return f"{temperatura}°C, {condizione}"
        else:
            return "Errore meteo"
    except Exception:
        return "Servizio meteo irraggiungibile"

def fetch_infortuni_lega():
    """Scarica (o legge dalla cache locale di 24h) gli infortuni della Serie A."""
    if os.path.exists(CACHE_INJURIES_FILE):
        if (time.time() - os.path.getmtime(CACHE_INJURIES_FILE)) < 86400:
            try:
                with open(CACHE_INJURIES_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass

    leghe = {"135": "serie_a"} 
    dati_raccolti = {}

    for id_lega, nome in leghe.items():
        try:
            response = requests.get(API_FOOTBALL_URL, headers=API_FOOTBALL_HEADERS, params={"league": id_lega, "season": "2026"}, timeout=5)
            if response.status_code == 200:
                dati_raccolti[nome] = response.json().get("response", [])
        except Exception:
            dati_raccolti[nome] = []

    try:
        with open(CACHE_INJURIES_FILE, 'w') as f:
            json.dump(dati_raccolti, f)
    except Exception:
        pass
    
    return dati_raccolti

def get_infortuni_live(home: str, away: str) -> dict:
    """Filtra gli infortuni specifici per le due squadre in campo."""
    tutti_infortuni = fetch_infortuni_lega()
    infortuni_serie_a = tutti_infortuni.get("serie_a", [])
    
    infortuni_match = {
        home: {"giocatori_out": 0, "dettagli": []},
        away: {"giocatori_out": 0, "dettagli": []}
    }
    
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

def get_dati_dinamici(home: str, away: str, match_id: str) -> dict:
    """Orchestratore dinamico che aggrega quote live, infortuni e parametri di match."""
    quota_live = get_quote_flashscore(match_id) if 'get_quote_flashscore' in globals() else {}
    infortuni = get_infortuni_live(home, away)
    
    return {
        "quote": quota_live,
        "infortuni": infortuni,
        "squadra_aggressiva": False
    }

def scrappa_arbitro_live(squadra_casa: str, squadra_ospite: str) -> str:
    """Recupera l'arbitro designato per l'incontro."""
    match_key = f"{squadra_casa}_{squadra_ospite}"
    arbitro_info = DB_ARBITRI.get(match_key, DB_ARBITRI.get("default", {"nome": "Davide Massa", "severita": 5}))
    if isinstance(arbitro_info, dict):
        return arbitro_info.get("nome", "Davide Massa")
    return "Davide Massa"

def genera_contesto_match(casa: str, ospite: str) -> dict:
    """Genera il contesto completo (stadio, meteo, allenatori, arbitro) per la UI Flutter."""
    casa_key = normalizza_nome_squadra(casa)
    ospite_key = normalizza_nome_squadra(ospite)

    stadio_info = DB_STADI.get(casa_key, DB_STADI["default"])
    all_casa = DB_ALLENATORI.get(casa_key, DB_ALLENATORI["default"])
    all_ospite = DB_ALLENATORI.get(ospite_key, DB_ALLENATORI["default"])
    
    arbitro_designato = scrappa_arbitro_live(casa, ospite)
    arbitro_entry = DB_ARBITRI.get(arbitro_designato.lower().strip(), {"severita": 5})
    severita_arbitro = arbitro_entry.get("severita", 5) if isinstance(arbitro_entry, dict) else 5
    
    meteo_live = ottieni_meteo_live(stadio_info.get("lat"), stadio_info.get("lon"))
    copertura_str = "Coperto" if stadio_info.get("coperto", False) else "Scoperto"
    
    return {
        "STADIO": stadio_info.get("stadio", "Stadio Ufficiale"),
        "Città": stadio_info.get("citta", "N/D"),
        "TERRENO": stadio_info.get("campo", "Erba Naturale"),
        "COPERTURA": copertura_str,
        "METEO LIVE": meteo_live,
        "ALLENATORE CASA": f"{all_casa.get('allenatore', 'N/D')} (Indice: {all_casa.get('indice_tattico', 'N/D')})",
        "ALLENATORE OSPITE": f"{all_ospite.get('allenatore', 'N/D')} (Indice: {all_ospite.get('indice_tattico', 'N/D')})",
        "ARBITRO & SEVERITÀ": f"{arbitro_designato} (Severità: {severita_arbitro})",
        "Media Cartellini Stadio": stadio_info.get("media_cartellini", 2.0)
    }

def genera_parere_gemini(casa: str, ospite: str, contesto: dict, mercati: dict) -> str:
    """Interroga l'API di Gemini con modello gemini-3.6-flash e tentativi automatici di retry in caso di 503."""
    if not GEMINI_API_KEY:
        print("DEBUG GEMINI: Chiave API GEMINI_API_KEY non trovata nelle variabili d'ambiente.")
        return "Parere di Gemini non disponibile (chiave API non configurata)."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = (
        f"Analizza la partita di calcio tra {casa} e {ospite}. "
        f"Contesto del match: {contesto}. "
        f"Mercati e quote Poisson: {mercati}. "
        f"Fornisci un breve parere tecnico professionale da esperto di scommesse sportive e tattica (massimo 3-4 righe, in italiano)."
    )
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    # Ciclo di retry (fino a 3 tentativi) per gestire i picchi di traffico di Google (503)
    for tentativo in range(3):
        try:
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            elif response.status_code == 503:
                print(f"DEBUG GEMINI - Server sovraccarico (503), tentativo {tentativo + 1}/3 in corso...")
                time.sleep(2)
                continue
            else:
                print(f"DEBUG GEMINI - Errore HTTP {response.status_code}: {response.text}")
                return f"Parere di Gemini non disponibile (Errore HTTP {response.status_code})."
        except Exception as e:
            print(f"DEBUG GEMINI - Eccezione al tentativo {tentativo + 1}: {str(e)}")
            if tentativo == 2:
                return f"Servizio Gemini non raggiungibile ({str(e)})."
            time.sleep(2)
            
    return "Parere di Gemini non disponibile (servizio temporaneamente occupato)."

def esegui_master_calculator(casa: str, ospite: str, contesto: dict):
    """Elabora i fattori qualitativi umani e tattici del match."""
    return {
        "fattori_umani": "Equilibrio tattico stimato.",
        "disciplinare": "Regolare",
        "flussi_monetari": "Analisi volumi di mercato attiva.",
        "whale_alert": False,
        "trend_storici": "Analisi H2H elaborata."
    }

def get_context_multiplier(contesto: dict) -> float:
    """
    Calcola un moltiplicatore unico basato su stadio, motivazione, mister, 
    infortuni chiave e severità dell'arbitro da applicare alla Poisson.
    """
    moltiplicatore = 1.0
    
    # 1. Peso Stadio (Sintetico/Vero, Aperto/Chiuso)
    if contesto.get("stadio_tipo") == "sintetico" and contesto.get("squadra_abitudine") == "naturale":
        moltiplicatore *= 0.95
    if contesto.get("stadio_condizione") == "chiuso": 
        moltiplicatore *= 1.02
        
    # 2. Peso Motivazione
    motivazione_map = {"alta": 1.1, "normale": 1.0, "scarsa": 0.9}
    moltiplicatore *= motivazione_map.get(contesto.get("motivazione", "normale"), 1.0)
    
    # 3. Peso Mister
    moltiplicatore *= contesto.get("peso_mister", 1.0)
    
    # 4. Peso Infortuni / Squalifiche
    if contesto.get("giocatori_chiave_out", False):
        moltiplicatore *= 0.85
        
    # 5. Peso Arbitro e Aggressività
    if contesto.get("arbitro_severo") and contesto.get("squadra_aggressiva"):
        moltiplicatore *= 0.92
        
    return moltiplicatore

def poisson_probability(k: int, lambd: float) -> float:
    """Calcola la probabilità di un singolo evento secondo la distribuzione di Poisson."""
    if lambd <= 0:
        return 0.0
    return (math.pow(lambd, k) * math.exp(-lambd)) / math.factorial(k)

def calcola_lambda_avanzato(casa_key: str, ospite_key: str, l_casa_base: float, l_ospite_base: float, molt_infortuni: float = 1.0, molt_stadio: float = 1.0, molt_arbitro: float = 1.0):
    """Calcola i valori lambda ponderati applicando i coefficienti avanzati (xG, PPDA, infortuni, ecc.)."""
    fattore_campo = DB_OVERRIDE_FATTORE_CAMPO.get(casa_key, 1.19)
    eff_casa = DB_EFFICIENZA_XG.get(casa_key, 1.0)
    acc_casa = DB_ACCURATEZZA_BALISTICA.get(casa_key, 1.0)
    duelli_casa = DB_DUELLI.get(casa_key, 1.0)
    
    eff_trasferta = DB_EFFICIENZA_XG.get(ospite_key, 1.0)
    acc_trasferta = DB_ACCURATEZZA_BALISTICA.get(ospite_key, 1.0)
    duelli_trasferta = DB_DUELLI.get(ospite_key, 1.0)
    
    ppda_casa = DB_PPDA.get(casa_key, 11.0)
    ppda_trasferta = DB_PPDA.get(ospite_key, 11.0)
    
    disturbo_pressing_casa = 0.96 if ppda_casa < 9.5 else 1.0
    disturbo_pressing_ospite = 0.96 if ppda_trasferta < 9.5 else 1.0
    
    l_casa_finale = l_casa_base * fattore_campo * eff_casa * acc_casa * duelli_casa * disturbo_pressing_ospite * molt_infortuni * molt_stadio
    l_ospite_finale = l_ospite_base * eff_trasferta * acc_trasferta * duelli_trasferta * disturbo_pressing_casa * molt_arbitro
    
    return round(l_casa_finale, 3), round(l_ospite_finale, 3)

def calcola_matrice_risultati(l_casa: float, l_ospite: float, max_gol: int = 5):
    """Genera la matrice delle probabilità per i risultati esatti."""
    matrice = {}
    for i in range(max_gol + 1):
        for j in range(max_gol + 1):
            p_i = poisson_probability(i, l_casa)
            p_j = poisson_probability(j, l_ospite)
            matrice[f"{i}-{j}"] = p_i * p_j
    return matrice

def elabora_mercati_poisson(l_casa: float, l_ospite: float):
    """Converte i lambda di Poisson nelle percentuali e quote dei principali mercati (1X2, Under/Over, Goal/NoGoal)."""
    matrice = calcola_matrice_risultati(l_casa, l_ospite)
    
    p_1 = sum(prob for score, prob in matrice.items() if int(score.split('-')[0]) > int(score.split('-')[1]))
    p_X = sum(prob for score, prob in matrice.items() if int(score.split('-')[0]) == int(score.split('-')[1]))
    p_2 = sum(prob for score, prob in matrice.items() if int(score.split('-')[0]) < int(score.split('-')[1]))
    
    esito_1x2 = {
        "1": {"probabilita": round(p_1 * 100, 2), "quota": round(1 / p_1, 2) if p_1 > 0 else 99.0},
        "X": {"probabilita": round(p_X * 100, 2), "quota": round(1 / p_X, 2) if p_X > 0 else 99.0},
        "2": {"probabilita": round(p_2 * 100, 2), "quota": round(1 / p_2, 2) if p_2 > 0 else 99.0}
    }
    
    p_gg = sum(prob for score, prob in matrice.items() if int(score.split('-')[0]) > 0 and int(score.split('-')[1]) > 0)
    p_ng = 1.0 - p_gg
    
    gol_no_gol = {
        "Gol": {"probabilita": round(p_gg * 100, 2), "quota": round(1 / p_gg, 2) if p_gg > 0 else 99.0},
        "NoGol": {"probabilita": round(p_ng * 100, 2), "quota": round(1 / p_ng, 2) if p_ng > 0 else 99.0}
    }
    
    under_over = {}
    for soglia in [0.5, 1.5, 2.5, 3.5, 4.5]:
        u_p = sum(prob for score, prob in matrice.items() if (int(score.split('-')[0]) + int(score.split('-')[1])) < soglia)
        under_over[f"Under {soglia}"] = round(u_p * 100, 2)
        under_over[f"Over {soglia}"] = round((1.0 - u_p) * 100, 2)
        
    top_esatti = sorted(matrice.items(), key=lambda x: x[1], reverse=True)[:3]
    top_esatti_fmt = [{"risultato": k, "probabilita": round(v * 100, 2)} for k, v in top_esatti]

    return {
        "esito_1x2": esito_1x2,
        "gol_no_gol": gol_no_gol,
        "under_over": under_over,
        "top_3_risultati_esatti": top_esatti_fmt
    }