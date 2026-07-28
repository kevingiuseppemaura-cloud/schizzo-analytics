import os
import math
import time
from functools import wraps
import requests
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup

# ==========================================
# ⏱️ SISTEMA DI CACHE INTELLIGENTE (60s TTL)
# ==========================================
def timed_cache(seconds: int = 60):
    def decorator(func):
        cache = {}
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < seconds:
                    return result
            result = func(*args, **kwargs)
            cache[key] = (result, now)
            return result
        return wrapper
    return decorator

# ==========================================
# 🌤️ CONFIGURAZIONE METEO (OPENWEATHERMAP)
# ==========================================
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "1276c6c958e9fa1f6d99da6fadb02421")

@timed_cache(seconds=60)
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
# 🔄 MAPPATURA ALIAS E NORMALIZZAZIONE
# ==========================================
TEAM_ALIASES = {
    # BUNDESLIGA
    "bayern munich": "bayern monaco",
    "fc bayern münchen": "bayern monaco",
    "borussia dortmund": "borussia",
    "bvb": "borussia",
    "borussia mgladbach": "borussia monchengladbach",
    "borussia mönchengladbach": "borussia monchengladbach",
    "mainz 05": "magonza",
    "fsv mainz 05": "magonza",
    "1. fc union berlin": "union berlino",
    "union berlin": "union berlino",
    "fc augsburg": "fc augusta",
    "augsburg": "fc augusta",
    "werder bremen": "werder brema",
    "sv werder bremen": "werder brema",
    "eintracht frankfurt": "eintracht francoforte",
    "vfb stuttgart": "stoccarda",
    "stuttgart": "stoccarda",
    "tsg hoffenheim": "hoffenheim",
    "tsg 1899 hoffenheim": "hoffenheim",
    "sc freiburg": "friburgo",
    "freiburg": "friburgo",
    "vfl wolfsburg": "wolfsburg",
    "vfl bochum": "bochum",
    "rb leipzig": "lipsia",
    "bayer 04 leverkusen": "bayer leverkusen",

    # LA LIGA
    "fc barcelona": "barcellona",
    "barcelona": "barcellona",
    "real madrid cf": "real madrid",
    "atletico madrid": "atletico madrid",
    "atlético de madrid": "atletico madrid",
    "athletic club": "athletic bilbao",
    "athletic bilbao": "athletic bilbao",
    "real betis balompié": "real betis",
    "betis": "real betis",
    "rcd espanyol": "espanyol",
    "rcd mallorca": "mallorca",
    "rayo vallecano": "rayo vallecano",
    "villarreal cf": "villarreal",
    "celta de vigo": "celta vigo",

    # LIGUE 1
    "paris saint-germain": "psg",
    "paris sg": "psg",
    "olympique lyonnais": "lyon",
    "olympique de marseille": "marseille",
    "stade de reims": "reims",
    "as monaco": "monaco",
    "stade rennais fc": "rennes",
    "ogc nice": "nice",

    # PREMIER LEAGUE
    "manchester city fc": "manchester city",
    "man city": "manchester city",
    "manchester united fc": "manchester united",
    "man utd": "manchester united",
    "tottenham hotspur": "tottenham",
    "spurs": "tottenham",
    "wolverhampton wanderers": "wolves",
    "brighton & hove albion": "brighton",
    "west ham united": "west ham",
    "nottingham forest": "nottingham",

    # SERIE A / B
    "internazionale": "inter",
    "ac milan": "milan",
    "juventus fc": "juventus",
    "as roma": "roma",
    "sslazio": "lazio",
    "hellas verona": "verona",
    "us cremonese": "cremonese",
    "ss juve stabia": "juve stabia"
}

def normalizza_nome_squadra(nome: str) -> str:
    if not nome:
        return "default"
    clean = nome.strip().lower()
    return TEAM_ALIASES.get(clean, clean)

# ==========================================
# 🗄️ DATABASE PROPRIETARI COMPLETI & FALLBACK
# ==========================================

DEFAULT_STADIO = {"stadio": "Stadio Generico", "citta": "N/D", "campo": "erba_naturale", "lat": 0.0, "lon": 0.0, "media_cartellini": 2.0, "coperto": False}
DEFAULT_ALLENATORE = {"allenatore": "Non dichiarato", "indice_tattico": 5}
DEFAULT_LAMBDA = {"lambda_casa": 1.35, "lambda_ospite": 1.00}

# 1. DATABASE STADI COMPLETO
DB_STADI = {
    "default": DEFAULT_STADIO,

    # --- SERIE A ---
    "atalanta": {"stadio": "Gewiss Stadium", "citta": "Bergamo", "campo": "erba_naturale", "lat": 45.71, "lon": 9.68, "media_cartellini": 2.4, "coperto": False},
    "bologna": {"stadio": "Stadio Renato Dall'Ara", "citta": "Bologna", "campo": "erba_naturale", "lat": 44.49, "lon": 11.31, "media_cartellini": 2.3, "coperto": False},
    "cagliari": {"stadio": "Unipol Domus", "citta": "Cagliari", "campo": "erba_naturale", "lat": 39.20, "lon": 9.13, "media_cartellini": 2.5, "coperto": False},
    "como": {"stadio": "Stadio Giuseppe Sinigaglia", "citta": "Como", "campo": "erba_naturale", "lat": 45.81, "lon": 9.07, "media_cartellini": 2.2, "coperto": False},
    "empoli": {"stadio": "Stadio Carlo Castellani", "citta": "Empoli", "campo": "erba_naturale", "lat": 43.72, "lon": 10.95, "media_cartellini": 2.1, "coperto": False},
    "fiorentina": {"stadio": "Stadio Artemio Franchi", "citta": "Firenze", "campo": "erba_naturale", "lat": 43.78, "lon": 11.28, "media_cartellini": 2.3, "coperto": False},
    "genoa": {"stadio": "Stadio Luigi Ferraris", "citta": "Genova", "campo": "erba_naturale", "lat": 44.42, "lon": 8.95, "media_cartellini": 2.4, "coperto": False},
    "verona": {"stadio": "Stadio Marcantonio Bentegodi", "citta": "Verona", "campo": "erba_naturale", "lat": 45.43, "lon": 10.97, "media_cartellini": 2.6, "coperto": False},
    "inter": {"stadio": "Stadio Giuseppe Meazza", "citta": "Milano", "campo": "erba_ibrida", "lat": 45.47, "lon": 9.12, "media_cartellini": 2.2, "coperto": False},
    "juventus": {"stadio": "Allianz Stadium", "citta": "Torino", "campo": "erba_naturale", "lat": 45.10, "lon": 7.64, "media_cartellini": 2.1, "coperto": False},
    "lazio": {"stadio": "Stadio Olimpico", "citta": "Roma", "campo": "erba_naturale", "lat": 41.93, "lon": 12.45, "media_cartellini": 2.5, "coperto": False},
    "lecce": {"stadio": "Stadio Via del Mare", "citta": "Lecce", "campo": "erba_naturale", "lat": 40.36, "lon": 18.18, "media_cartellini": 2.4, "coperto": False},
    "milan": {"stadio": "Stadio Giuseppe Meazza", "citta": "Milano", "campo": "erba_ibrida", "lat": 45.47, "lon": 9.12, "media_cartellini": 2.3, "coperto": False},
    "monza": {"stadio": "U-Power Stadium", "citta": "Monza", "campo": "erba_naturale", "lat": 45.58, "lon": 9.27, "media_cartellini": 2.2, "coperto": False},
    "napoli": {"stadio": "Stadio Diego Armando Maradona", "citta": "Napoli", "campo": "erba_naturale", "lat": 40.82, "lon": 14.19, "media_cartellini": 2.4, "coperto": False},
    "parma": {"stadio": "Stadio Ennio Tardini", "citta": "Parma", "campo": "erba_naturale", "lat": 44.79, "lon": 10.33, "media_cartellini": 2.2, "coperto": False},
    "roma": {"stadio": "Stadio Olimpico", "citta": "Roma", "campo": "erba_naturale", "lat": 41.93, "lon": 12.45, "media_cartellini": 2.5, "coperto": False},
    "torino": {"stadio": "Stadio Olimpico Grande Torino", "citta": "Torino", "campo": "erba_naturale", "lat": 45.03, "lon": 7.65, "media_cartellini": 2.3, "coperto": False},
    "udinese": {"stadio": "Bluenergy Stadium", "citta": "Udine", "campo": "erba_naturale", "lat": 46.06, "lon": 13.19, "media_cartellini": 2.6, "coperto": True},
    "venezia": {"stadio": "Stadio Pier Luigi Penzo", "citta": "Venezia", "campo": "erba_naturale", "lat": 45.42, "lon": 12.36, "media_cartellini": 2.3, "coperto": False},

    # --- SERIE B ---
    "bari": {"stadio": "Stadio San Nicola", "citta": "Bari", "campo": "erba_naturale", "lat": 41.09, "lon": 16.84, "media_cartellini": 2.5, "coperto": False},
    "brescia": {"stadio": "Stadio Mario Rigamonti", "citta": "Brescia", "campo": "erba_naturale", "lat": 45.56, "lon": 10.23, "media_cartellini": 2.6, "coperto": False},
    "carrarese": {"stadio": "Stadio Dei Marmi", "citta": "Carrara", "campo": "sintetico", "lat": 44.05, "lon": 10.10, "media_cartellini": 2.4, "coperto": False},
    "catanzaro": {"stadio": "Stadio Nicola Ceravolo", "citta": "Catanzaro", "campo": "erba_naturale", "lat": 38.91, "lon": 16.58, "media_cartellini": 2.5, "coperto": False},
    "cesena": {"stadio": "Orogel Stadium-Dino Manuzzi", "citta": "Cesena", "campo": "sintetico", "lat": 44.14, "lon": 12.26, "media_cartellini": 2.3, "coperto": False},
    "cittadella": {"stadio": "Stadio Pier Cesare Tombolato", "citta": "Cittadella", "campo": "erba_naturale", "lat": 45.65, "lon": 11.78, "media_cartellini": 2.4, "coperto": False},
    "cosenza": {"stadio": "Stadio San Vito-Gigi Marulla", "citta": "Cosenza", "campo": "erba_naturale", "lat": 39.30, "lon": 16.23, "media_cartellini": 2.7, "coperto": False},
    "cremonese": {"stadio": "Stadio Giovanni Zini", "citta": "Cremona", "campo": "erba_naturale", "lat": 45.13, "lon": 10.03, "media_cartellini": 2.3, "coperto": False},
    "frosinone": {"stadio": "Stadio Benito Stirpe", "citta": "Frosinone", "campo": "erba_naturale", "lat": 41.63, "lon": 13.34, "media_cartellini": 2.6, "coperto": False},
    "juve stabia": {"stadio": "Stadio Romeo Menti", "citta": "Castellammare di Stabia", "campo": "sintetico", "lat": 40.70, "lon": 14.48, "media_cartellini": 2.6, "coperto": False},
    "mantova": {"stadio": "Stadio Danilo Martelli", "citta": "Mantova", "campo": "erba_naturale", "lat": 45.14, "lon": 10.79, "media_cartellini": 2.2, "coperto": False},
    "modena": {"stadio": "Stadio Alberto Braglia", "citta": "Modena", "campo": "erba_naturale", "lat": 44.65, "lon": 10.92, "media_cartellini": 2.4, "coperto": False},
    "palermo": {"stadio": "Stadio Renzo Barbera", "citta": "Palermo", "campo": "erba_naturale", "lat": 38.15, "lon": 13.34, "media_cartellini": 2.5, "coperto": False},
    "pisa": {"stadio": "Stadio Arena Garibaldi-Romeo Anconetani", "citta": "Pisa", "campo": "erba_naturale", "lat": 43.72, "lon": 10.40, "media_cartellini": 2.5, "coperto": False},
    "reggiana": {"stadio": "Mapei Stadium", "citta": "Reggio Emilia", "campo": "erba_ibrida", "lat": 44.71, "lon": 10.64, "media_cartellini": 2.3, "coperto": False},
    "salernitana": {"stadio": "Stadio Arechi", "citta": "Salerno", "campo": "erba_naturale", "lat": 40.64, "lon": 14.82, "media_cartellini": 2.6, "coperto": False},
    "sampdoria": {"stadio": "Stadio Luigi Ferraris", "citta": "Genova", "campo": "erba_naturale", "lat": 44.42, "lon": 8.95, "media_cartellini": 2.5, "coperto": False},
    "sassuolo": {"stadio": "Mapei Stadium", "citta": "Reggio Emilia", "campo": "erba_ibrida", "lat": 44.71, "lon": 10.64, "media_cartellini": 2.2, "coperto": False},
    "spezia": {"stadio": "Stadio Alberto Picco", "citta": "La Spezia", "campo": "erba_ibrida", "lat": 44.10, "lon": 9.81, "media_cartellini": 2.6, "coperto": False},
    "sudtirol": {"stadio": "Stadio Druso", "citta": "Bolzano", "campo": "erba_naturale", "lat": 46.49, "lon": 11.35, "media_cartellini": 2.2, "coperto": False},

    # --- PREMIER LEAGUE ---
    "arsenal": {"stadio": "Emirates Stadium", "citta": "London", "campo": "erba_naturale", "lat": 51.55, "lon": -0.10, "media_cartellini": 1.9, "coperto": False},
    "aston villa": {"stadio": "Villa Park", "citta": "Birmingham", "campo": "erba_naturale", "lat": 52.50, "lon": -1.88, "media_cartellini": 2.2, "coperto": False},
    "bournemouth": {"stadio": "Vitality Stadium", "citta": "Bournemouth", "campo": "erba_naturale", "lat": 50.73, "lon": -1.83, "media_cartellini": 2.1, "coperto": False},
    "brentford": {"stadio": "Gtech Community Stadium", "citta": "London", "campo": "erba_ibrida", "lat": 51.49, "lon": -0.28, "media_cartellini": 2.0, "coperto": False},
    "brighton": {"stadio": "Amex Stadium", "citta": "Brighton", "campo": "erba_ibrida", "lat": 50.86, "lon": -0.08, "media_cartellini": 2.1, "coperto": False},
    "chelsea": {"stadio": "Stamford Bridge", "citta": "London", "campo": "erba_naturale", "lat": 51.48, "lon": -0.19, "media_cartellini": 2.4, "coperto": False},
    "crystal palace": {"stadio": "Selhurst Park", "citta": "London", "campo": "erba_naturale", "lat": 51.39, "lon": -0.08, "media_cartellini": 2.2, "coperto": False},
    "everton": {"stadio": "Goodison Park", "citta": "Liverpool", "campo": "erba_naturale", "lat": 53.43, "lon": -2.96, "media_cartellini": 2.3, "coperto": False},
    "fulham": {"stadio": "Craven Cottage", "citta": "London", "campo": "erba_naturale", "lat": 51.47, "lon": -0.22, "media_cartellini": 2.1, "coperto": False},
    "ipswich": {"stadio": "Portman Road", "citta": "Ipswich", "campo": "erba_naturale", "lat": 52.05, "lon": 1.14, "media_cartellini": 2.2, "coperto": False},
    "leicester": {"stadio": "King Power Stadium", "citta": "Leicester", "campo": "erba_ibrida", "lat": 52.62, "lon": -1.14, "media_cartellini": 2.0, "coperto": False},
    "liverpool": {"stadio": "Anfield", "citta": "Liverpool", "campo": "erba_naturale", "lat": 53.43, "lon": -2.96, "media_cartellini": 1.8, "coperto": False},
    "manchester city": {"stadio": "Etihad Stadium", "citta": "Manchester", "campo": "erba_ibrida", "lat": 53.48, "lon": -2.20, "media_cartellini": 1.7, "coperto": False},
    "manchester united": {"stadio": "Old Trafford", "citta": "Manchester", "campo": "erba_naturale", "lat": 53.46, "lon": -2.29, "media_cartellini": 2.3, "coperto": False},
    "newcastle": {"stadio": "St James' Park", "citta": "Newcastle upon Tyne", "campo": "erba_naturale", "lat": 54.97, "lon": -1.62, "media_cartellini": 2.2, "coperto": False},
    "nottingham": {"stadio": "City Ground", "citta": "Nottingham", "campo": "erba_naturale", "lat": 52.94, "lon": -1.13, "media_cartellini": 2.3, "coperto": False},
    "southampton": {"stadio": "St Mary's Stadium", "citta": "Southampton", "campo": "erba_ibrida", "lat": 50.90, "lon": -1.39, "media_cartellini": 2.1, "coperto": False},
    "tottenham": {"stadio": "Tottenham Hotspur Stadium", "citta": "London", "campo": "erba_naturale", "lat": 51.60, "lon": -0.06, "media_cartellini": 2.3, "coperto": True},
    "west ham": {"stadio": "London Stadium", "citta": "London", "campo": "erba_ibrida", "lat": 51.53, "lon": -0.01, "media_cartellini": 2.2, "coperto": False},
    "wolves": {"stadio": "Molineux Stadium", "citta": "Wolverhampton", "campo": "erba_naturale", "lat": 52.59, "lon": -2.13, "media_cartellini": 2.4, "coperto": False},

    # --- BUNDESLIGA ---
    "bayern monaco": {"stadio": "Allianz Arena", "citta": "Munich", "campo": "erba_naturale", "lat": 48.21, "lon": 11.62, "media_cartellini": 1.8, "coperto": False},
    "borussia": {"stadio": "Signal Iduna Park", "citta": "Dortmund", "campo": "erba_naturale", "lat": 51.49, "lon": 7.45, "media_cartellini": 2.0, "coperto": False},
    "bayer leverkusen": {"stadio": "BayArena", "citta": "Leverkusen", "campo": "erba_naturale", "lat": 51.03, "lon": 7.00, "media_cartellini": 1.9, "coperto": False},
    "lipsia": {"stadio": "Red Bull Arena", "citta": "Leipzig", "campo": "erba_naturale", "lat": 51.34, "lon": 12.34, "media_cartellini": 2.2, "coperto": False},
    "eintracht francoforte": {"stadio": "Deutsche Bank Park", "citta": "Frankfurt", "campo": "erba_naturale", "lat": 50.06, "lon": 8.64, "media_cartellini": 2.3, "coperto": True},
    "wolfsburg": {"stadio": "Volkswagen Arena", "citta": "Wolfsburg", "campo": "erba_naturale", "lat": 52.43, "lon": 10.80, "media_cartellini": 2.1, "coperto": False},
    "borussia monchengladbach": {"stadio": "Borussia-Park", "citta": "Monchengladbach", "campo": "erba_naturale", "lat": 51.16, "lon": 6.38, "media_cartellini": 2.0, "coperto": False},
    "friburgo": {"stadio": "Europa-Park Stadion", "citta": "Freiburg", "campo": "erba_naturale", "lat": 48.01, "lon": 7.82, "media_cartellini": 1.9, "coperto": False},
    "hoffenheim": {"stadio": "PreZero Arena", "citta": "Sinsheim", "campo": "erba_naturale", "lat": 49.23, "lon": 8.87, "media_cartellini": 2.2, "coperto": False},
    "stoccarda": {"stadio": "MHPArena", "citta": "Stuttgart", "campo": "erba_naturale", "lat": 48.79, "lon": 9.23, "media_cartellini": 2.0, "coperto": False},
    "werder brema": {"stadio": "Wohninvest Weserstadion", "citta": "Bremen", "campo": "erba_naturale", "lat": 53.06, "lon": 8.83, "media_cartellini": 2.1, "coperto": False},
    "fc augusta": {"stadio": "WWK Arena", "citta": "Augsburg", "campo": "erba_naturale", "lat": 48.32, "lon": 10.88, "media_cartellini": 2.4, "coperto": False},
    "magonza": {"stadio": "Mewa Arena", "citta": "Mainz", "campo": "erba_naturale", "lat": 49.98, "lon": 8.22, "media_cartellini": 2.3, "coperto": False},
    "union berlino": {"stadio": "Stadion An der Alten Forsterei", "citta": "Berlin", "campo": "erba_naturale", "lat": 52.45, "lon": 13.56, "media_cartellini": 2.4, "coperto": False},
    "bochum": {"stadio": "Vonovia Ruhrstadion", "citta": "Bochum", "campo": "erba_naturale", "lat": 51.49, "lon": 7.23, "media_cartellini": 2.5, "coperto": False},
    "heidenheim": {"stadio": "Voith-Arena", "citta": "Heidenheim", "campo": "erba_naturale", "lat": 48.66, "lon": 10.13, "media_cartellini": 2.1, "coperto": False},
    "st. pauli": {"stadio": "Millerntor-Stadion", "citta": "Hamburg", "campo": "erba_naturale", "lat": 53.55, "lon": 9.96, "media_cartellini": 2.3, "coperto": False},
    "holstein kiel": {"stadio": "Holstein-Stadion", "citta": "Kiel", "campo": "erba_naturale", "lat": 54.34, "lon": 10.12, "media_cartellini": 2.2, "coperto": False},

    # --- LA LIGA ---
    "real madrid": {"stadio": "Santiago Bernabeu", "citta": "Madrid", "campo": "erba_ibrida", "lat": 40.45, "lon": -3.68, "media_cartellini": 1.9, "coperto": True},
    "barcellona": {"stadio": "Estadi Olimpic Lluis Companys", "citta": "Barcelona", "campo": "erba_naturale", "lat": 41.36, "lon": 2.15, "media_cartellini": 2.0, "coperto": False},
    "atletico madrid": {"stadio": "Metropolitano", "citta": "Madrid", "campo": "erba_naturale", "lat": 40.43, "lon": -3.59, "media_cartellini": 2.5, "coperto": False},
    "athletic bilbao": {"stadio": "San Mames", "citta": "Bilbao", "campo": "erba_naturale", "lat": 43.26, "lon": -2.94, "media_cartellini": 2.2, "coperto": False},
    "villarreal": {"stadio": "Estadio de la Ceramica", "citta": "Villarreal", "campo": "erba_naturale", "lat": 39.94, "lon": -0.10, "media_cartellini": 2.3, "coperto": False},
    "real sociedad": {"stadio": "Reale Arena", "citta": "San Sebastian", "campo": "erba_naturale", "lat": 43.30, "lon": -1.97, "media_cartellini": 2.1, "coperto": False},
    "real betis": {"stadio": "Benito Villamarin", "citta": "Seville", "campo": "erba_naturale", "lat": 37.35, "lon": -5.98, "media_cartellini": 2.4, "coperto": False},
    "sevilla": {"stadio": "Ramon Sanchez-Pizjuan", "citta": "Seville", "campo": "erba_naturale", "lat": 37.38, "lon": -5.97, "media_cartellini": 2.6, "coperto": False},
    "girona": {"stadio": "Montilivi", "citta": "Girona", "campo": "erba_naturale", "lat": 41.96, "lon": 2.82, "media_cartellini": 2.2, "coperto": False},
    "valencia": {"stadio": "Mestalla", "citta": "Valencia", "campo": "erba_naturale", "lat": 39.47, "lon": -0.35, "media_cartellini": 2.5, "coperto": False},
    "alaves": {"stadio": "Mendizorrotza", "citta": "Vitoria-Gasteiz", "campo": "erba_naturale", "lat": 42.83, "lon": -2.68, "media_cartellini": 2.4, "coperto": False},
    "celta vigo": {"stadio": "Abanca-Balaidos", "citta": "Vigo", "campo": "erba_naturale", "lat": 42.21, "lon": -8.73, "media_cartellini": 2.3, "coperto": False},
    "espanyol": {"stadio": "RCDE Stadium", "citta": "Barcelona", "campo": "erba_naturale", "lat": 41.34, "lon": 2.07, "media_cartellini": 2.5, "coperto": False},
    "getafe": {"stadio": "Coliseum", "citta": "Getafe", "campo": "erba_naturale", "lat": 40.32, "lon": -3.71, "media_cartellini": 2.8, "coperto": False},
    "las palmas": {"stadio": "Estadio Gran Canaria", "citta": "Las Palmas", "campo": "erba_naturale", "lat": 28.10, "lon": -15.45, "media_cartellini": 2.2, "coperto": False},
    "leganes": {"stadio": "Estadio Municipal de Butarque", "citta": "Leganes", "campo": "erba_naturale", "lat": 40.34, "lon": -3.76, "media_cartellini": 2.4, "coperto": False},
    "mallorca": {"stadio": "Estadi Mallorca Son Moix", "citta": "Palma", "campo": "erba_naturale", "lat": 39.58, "lon": 2.63, "media_cartellini": 2.6, "coperto": False},
    "osasuna": {"stadio": "El Sadar", "citta": "Pamplona", "campo": "erba_naturale", "lat": 42.79, "lon": -1.63, "media_cartellini": 2.3, "coperto": False},
    "rayo vallecano": {"stadio": "Campo de Futbol de Vallecas", "citta": "Madrid", "campo": "erba_naturale", "lat": 40.39, "lon": -3.65, "media_cartellini": 2.6, "coperto": False},
    "valladolid": {"stadio": "Estadio Jose Zorrilla", "citta": "Valladolid", "campo": "erba_naturale", "lat": 41.64, "lon": -4.76, "media_cartellini": 2.4, "coperto": False},

    # --- LIGUE 1 ---
    "psg": {"stadio": "Parc des Princes", "citta": "Paris", "campo": "erba_ibrida", "lat": 48.84, "lon": 2.25, "media_cartellini": 1.7, "coperto": False},
    "lyon": {"stadio": "Groupama Stadium", "citta": "Lyon", "campo": "erba_ibrida", "lat": 45.76, "lon": 4.97, "media_cartellini": 2.1, "coperto": False},
    "marseille": {"stadio": "Stade Velodrome", "citta": "Marseille", "campo": "erba_naturale", "lat": 43.26, "lon": 5.39, "media_cartellini": 2.4, "coperto": False},
    "monaco": {"stadio": "Stade Louis II", "citta": "Monaco", "campo": "erba_naturale", "lat": 43.72, "lon": 7.41, "media_cartellini": 1.9, "coperto": False},
    "angers": {"stadio": "Stade Raymond Kopa", "citta": "Angers", "campo": "erba_naturale", "lat": 47.46, "lon": -0.53, "media_cartellini": 2.2, "coperto": False},
    "auxerre": {"stadio": "Stade de l'Abbe-Deschamps", "citta": "Auxerre", "campo": "erba_naturale", "lat": 47.78, "lon": 3.58, "media_cartellini": 2.3, "coperto": False},
    "brest": {"stadio": "Stade Francis-Le Ble", "citta": "Brest", "campo": "erba_naturale", "lat": 48.40, "lon": -4.46, "media_cartellini": 2.1, "coperto": False},
    "le havre": {"stadio": "Stade Océane", "citta": "Le Havre", "campo": "erba_ibrida", "lat": 49.50, "lon": 0.16, "media_cartellini": 2.2, "coperto": False},
    "lens": {"stadio": "Stade Bollaert-Delelis", "citta": "Lens", "campo": "erba_naturale", "lat": 50.43, "lon": 2.81, "media_cartellini": 2.0, "coperto": False},
    "lille": {"stadio": "Decathlon Arena-Stade Pierre-Mauroy", "citta": "Lille", "campo": "erba_ibrida", "lat": 50.61, "lon": 3.13, "media_cartellini": 2.1, "coperto": True},
    "montpellier": {"stadio": "Stade de la Mosson", "citta": "Montpellier", "campo": "erba_naturale", "lat": 43.61, "lon": 3.81, "media_cartellini": 2.5, "coperto": False},
    "nantes": {"stadio": "Stade de la Beaujoire", "citta": "Nantes", "campo": "erba_naturale", "lat": 47.25, "lon": -1.52, "media_cartellini": 2.2, "coperto": False},
    "nice": {"stadio": "Allianz Riviera", "citta": "Nice", "campo": "erba_ibrida", "lat": 43.70, "lon": 7.19, "media_cartellini": 2.0, "coperto": False},
    "reims": {"stadio": "Stade Auguste-Delaune", "citta": "Reims", "campo": "erba_naturale", "lat": 49.24, "lon": 4.02, "media_cartellini": 2.1, "coperto": False},
    "rennes": {"stadio": "Roazhon Park", "citta": "Rennes", "campo": "erba_naturale", "lat": 48.10, "lon": -1.71, "media_cartellini": 2.0, "coperto": False},
    "saint-etienne": {"stadio": "Stade Geoffroy-Guichard", "citta": "Saint-Etienne", "campo": "erba_naturale", "lat": 45.46, "lon": 4.39, "media_cartellini": 2.4, "coperto": False},
    "strasbourg": {"stadio": "Stade de la Meinau", "citta": "Strasbourg", "campo": "erba_naturale", "lat": 48.55, "lon": 7.75, "media_cartellini": 2.2, "coperto": False},
    "toulouse": {"stadio": "Stadium de Toulouse", "citta": "Toulouse", "campo": "erba_naturale", "lat": 43.58, "lon": 1.43, "media_cartellini": 2.3, "coperto": False}
}

# 2. DATABASE ALLENATORI COMPLETO
DB_ALLENATORI = {
    # --- SERIE A ---
    "atalanta": {"allenatore": "Maurizio Sarri", "indice_tattico": 8},
    "bologna": {"allenatore": "Domenico Tedesco", "indice_tattico": 6},
    "cagliari": {"allenatore": "Fabio Pisacane", "indice_tattico": 5},
    "como": {"allenatore": "Cesc Fàbregas", "indice_tattico": 8},
    "fiorentina": {"allenatore": "Fabio Grosso", "indice_tattico": 6},
    "frosinone": {"allenatore": "Massimiliano Alvini", "indice_tattico": 5},
    "genoa": {"allenatore": "Daniele De Rossi", "indice_tattico": 6},
    "inter": {"allenatore": "Cristian Chivu", "indice_tattico": 6},
    "juventus": {"allenatore": "Luciano Spalletti", "indice_tattico": 8},
    "lazio": {"allenatore": "Gennaro Gattuso", "indice_tattico": 6},
    "lecce": {"allenatore": "Eusebio Di Francesco", "indice_tattico": 6},
    "milan": {"allenatore": "Ruben Amorim", "indice_tattico": 8},
    "monza": {"allenatore": "Ivan Juric", "indice_tattico": 8},
    "napoli": {"allenatore": "Massimiliano Allegri", "indice_tattico": 4},
    "parma": {"allenatore": "Carlos Cuesta", "indice_tattico": 6},
    "roma": {"allenatore": "Gian Piero Gasperini", "indice_tattico": 10},
    "sassuolo": {"allenatore": "Alberto Aquilani", "indice_tattico": 7},
    "torino": {"allenatore": "Ignazio Abate", "indice_tattico": 6},
    "udinese": {"allenatore": "Kosta Runjaic", "indice_tattico": 6},
    "venezia": {"allenatore": "Giovanni Stroppa", "indice_tattico": 6},

    # --- SERIE B ---
    "arezzo": {"allenatore": "Cristian Bucchi", "indice_tattico": 5},
    "ascoli": {"allenatore": "Daniele Tomei", "indice_tattico": 5},
    "avellino": {"allenatore": "Alessandro Nesta", "indice_tattico": 5},
    "benevento": {"allenatore": "Antonio Floro Flores", "indice_tattico": 6},
    "carrarese": {"allenatore": "Antonio Cioffi", "indice_tattico": 5},
    "catanzaro": {"allenatore": "Giorgio Gorgone", "indice_tattico": 6},
    "cesena": {"allenatore": "Alessandro Diamanti", "indice_tattico": 6},
    "cremonese": {"allenatore": "Marco Giampaolo", "indice_tattico": 6},
    "empoli": {"allenatore": "Guido Pagliuca", "indice_tattico": 6},
    "entella": {"allenatore": "Simone Chiappella", "indice_tattico": 5},
    "juve stabia": {"allenatore": "Ignazio De Giorgio", "indice_tattico": 5},
    "mantova": {"allenatore": "Francesco Modesto", "indice_tattico": 7},
    "modena": {"allenatore": "Alberto Galloppa", "indice_tattico": 6},
    "padova": {"allenatore": "Antonio Calabro", "indice_tattico": 5},
    "palermo": {"allenatore": "Filippo Inzaghi", "indice_tattico": 5},
    "pisa": {"allenatore": "Paolo Bianco", "indice_tattico": 5},
    "sampdoria": {"allenatore": "Bernardo Corradi", "indice_tattico": 5},
    "sudtirol": {"allenatore": "Matteo Possanzini", "indice_tattico": 6},
    "verona": {"allenatore": "Marco Baroni", "indice_tattico": 5},
    "vicenza": {"allenatore": "Fabio Gallo", "indice_tattico": 5},

    # --- PREMIER LEAGUE ---
    "arsenal": {"allenatore": "Mikel Arteta", "indice_tattico": 8},
    "aston villa": {"allenatore": "Unai Emery", "indice_tattico": 9},
    "bournemouth": {"allenatore": "Andoni Iraola", "indice_tattico": 8},
    "brentford": {"allenatore": "Thomas Frank", "indice_tattico": 6},
    "brighton": {"allenatore": "Fabian Hürzeler", "indice_tattico": 8},
    "chelsea": {"allenatore": "Enzo Maresca", "indice_tattico": 7},
    "crystal palace": {"allenatore": "Oliver Glasner", "indice_tattico": 7},
    "everton": {"allenatore": "Sean Dyche", "indice_tattico": 2},
    "fulham": {"allenatore": "Marco Silva", "indice_tattico": 6},
    "ipswich town": {"allenatore": "Kieran McKenna", "indice_tattico": 7},
    "leicester city": {"allenatore": "Ruud van Nistelrooy", "indice_tattico": 5},
    "liverpool": {"allenatore": "Arne Slot", "indice_tattico": 8},
    "manchester city": {"allenatore": "Pep Guardiola", "indice_tattico": 10},
    "manchester united": {"allenatore": "Rúben Amorim", "indice_tattico": 8},
    "newcastle united": {"allenatore": "Eddie Howe", "indice_tattico": 7},
    "nottingham forest": {"allenatore": "Nuno Espírito Santo", "indice_tattico": 4},
    "southampton": {"allenatore": "Russell Martin", "indice_tattico": 7},
    "tottenham": {"allenatore": "Ange Postecoglou", "indice_tattico": 10},
    "west ham": {"allenatore": "Julen Lopetegui", "indice_tattico": 5},
    "wolverhampton": {"allenatore": "Gary O'Neil", "indice_tattico": 5},

    # --- BUNDESLIGA ---
    "stoccarda": {"allenatore": "Sebastian Hoeneß", "indice_tattico": 9},
    "bayern monaco": {"allenatore": "Vincent Kompany", "indice_tattico": 9},
    "friburgo": {"allenatore": "Julian Schuster", "indice_tattico": 6},
    "hoffenheim": {"allenatore": "Christian Ilzer", "indice_tattico": 7},
    "amburgo": {"allenatore": "Merlin Polzin", "indice_tattico": 6},
    "borussia": {"allenatore": "Niko Kovac", "indice_tattico": 4},
    "schalke": {"allenatore": "Miron Muslic", "indice_tattico": 6},
    "elversberg": {"allenatore": "Vincent Wagner", "indice_tattico": 5},
    "paderborn": {"allenatore": "Ralf Kettemann", "indice_tattico": 6},
    "borussia monchengladbach": {"allenatore": "Eugen Polanski", "indice_tattico": 6},
    "magonza": {"allenatore": "Urs Fischer", "indice_tattico": 3},
    "werder brema": {"allenatore": "Daniel Thioune", "indice_tattico": 5},
    "fc augusta": {"allenatore": "Manuel Baum", "indice_tattico": 5},
    "colonia": {"allenatore": "René Wagner", "indice_tattico": 5},
    "lipsia": {"allenatore": "Martín Demichelis", "indice_tattico": 7},
    "union berlino": {"allenatore": "Mauro Lustrinelli", "indice_tattico": 4},
    "eintracht francoforte": {"allenatore": "Adi Hütter", "indice_tattico": 8},
    "bayer leverkusen": {"allenatore": "Carles Martínez", "indice_tattico": 8},

    # --- LA LIGA ---
    "real madrid": {"allenatore": "Carlo Ancelotti", "indice_tattico": 6},
    "barcellona": {"allenatore": "Hansi Flick", "indice_tattico": 10},
    "atletico madrid": {"allenatore": "Diego Simeone", "indice_tattico": 4},
    "athletic bilbao": {"allenatore": "Ernesto Valverde", "indice_tattico": 7},
    "girona": {"allenatore": "Míchel", "indice_tattico": 9},
    "real sociedad": {"allenatore": "Imanol Alguacil", "indice_tattico": 7},
    "real betis": {"allenatore": "Manuel Pellegrini", "indice_tattico": 6},
    "villarreal": {"allenatore": "Marcelino", "indice_tattico": 6},
    "valencia": {"allenatore": "Rubén Baraja", "indice_tattico": 4},
    "sevilla": {"allenatore": "García Pimienta", "indice_tattico": 8},
    "celta vigo": {"allenatore": "Claudio Giráldez", "indice_tattico": 6},
    "osasuna": {"allenatore": "Vicente Moreno", "indice_tattico": 4},
    "mallorca": {"allenatore": "Jagoba Arrasate", "indice_tattico": 5},
    "rayo vallecano": {"allenatore": "Íñigo Pérez", "indice_tattico": 6},
    "getafe": {"allenatore": "José Bordalás", "indice_tattico": 2},
    "alaves": {"allenatore": "Luis García Plaza", "indice_tattico": 5},
    "las palmas": {"allenatore": "Dinko Jeličić", "indice_tattico": 5},
    "almeria": {"allenatore": "Xavi García Pimienta", "indice_tattico": 7},
    "granada": {"allenatore": "Pacheta", "indice_tattico": 6},
    "cadice": {"allenatore": "Imanol Idiakez", "indice_tattico": 5},

    # --- LIGUE 1 ---
    "paris saint-germain": {"allenatore": "Luis Enrique", "indice_tattico": 9},
    "marseille": {"allenatore": "Roberto De Zerbi", "indice_tattico": 9},
    "monaco": {"allenatore": "Adi Hütter", "indice_tattico": 8},
    "lille": {"allenatore": "Bruno Génésio", "indice_tattico": 6},
    "lyon": {"allenatore": "Pierre Sage", "indice_tattico": 7},
    "nice": {"allenatore": "Franck Haise", "indice_tattico": 6},
    "brest": {"allenatore": "Eric Roy", "indice_tattico": 4},
    "lens": {"allenatore": "Will Still", "indice_tattico": 6},
    "strasbourg": {"allenatore": "Liam Rosenior", "indice_tattico": 6},
    "toulouse": {"allenatore": "Carles Martínez Novell", "indice_tattico": 5},
    "rennes": {"allenatore": "Julien Stéphan", "indice_tattico": 6},
    "reims": {"allenatore": "Luka Elsner", "indice_tattico": 5},
    "nantes": {"allenatore": "Antoine Kombouaré", "indice_tattico": 4},
    "montpellier": {"allenatore": "Jean-Louis Gasset", "indice_tattico": 5},
    "saint-etienne": {"allenatore": "Olivier Dall'Oglio", "indice_tattico": 5},
    "le havre": {"allenatore": "Didier Digard", "indice_tattico": 4},
    "angers": {"allenatore": "Alexandre Dujeux", "indice_tattico": 4},
    "auxerre": {"allenatore": "Christophe Pélissier", "indice_tattico": 5}
}

# 3. DATABASE STATS LAMBDA GOL ATTESI COMPLETO
DB_LAMBDA_SQUADRE = {
    "default": DEFAULT_LAMBDA,

    # SERIE A
    "inter": {"lambda_casa": 2.10, "lambda_ospite": 1.75},
    "milan": {"lambda_casa": 1.80, "lambda_ospite": 1.40},
    "juventus": {"lambda_casa": 1.65, "lambda_ospite": 1.20},
    "napoli": {"lambda_casa": 1.85, "lambda_ospite": 1.45},
    "roma": {"lambda_casa": 1.70, "lambda_ospite": 1.25},
    "lazio": {"lambda_casa": 1.55, "lambda_ospite": 1.15},
    "atalanta": {"lambda_casa": 2.00, "lambda_ospite": 1.60},
    "fiorentina": {"lambda_casa": 1.50, "lambda_ospite": 1.10},
    "bologna": {"lambda_casa": 1.45, "lambda_ospite": 1.05},
    "torino": {"lambda_casa": 1.25, "lambda_ospite": 0.90},
    "verona": {"lambda_casa": 1.10, "lambda_ospite": 0.85},
    "udinese": {"lambda_casa": 1.20, "lambda_ospite": 0.95},
    "genoa": {"lambda_casa": 1.15, "lambda_ospite": 0.85},
    "monza": {"lambda_casa": 1.10, "lambda_ospite": 0.80},
    "cagliari": {"lambda_casa": 1.15, "lambda_ospite": 0.75},
    "empoli": {"lambda_casa": 1.00, "lambda_ospite": 0.70},
    "lecce": {"lambda_casa": 1.05, "lambda_ospite": 0.70},
    "parma": {"lambda_casa": 1.20, "lambda_ospite": 0.90},
    "como": {"lambda_casa": 1.10, "lambda_ospite": 0.85},
    "venezia": {"lambda_casa": 1.00, "lambda_ospite": 0.75},

    # SERIE B
    "frosinone": {"lambda_casa": 1.35, "lambda_ospite": 1.05},
    "sassuolo": {"lambda_casa": 1.45, "lambda_ospite": 1.15},
    "salernitana": {"lambda_casa": 1.25, "lambda_ospite": 0.95},
    "palermo": {"lambda_casa": 1.40, "lambda_ospite": 1.10},
    "cremonese": {"lambda_casa": 1.35, "lambda_ospite": 1.05},
    "sampdoria": {"lambda_casa": 1.30, "lambda_ospite": 1.00},
    "brescia": {"lambda_casa": 1.20, "lambda_ospite": 0.90},
    "bari": {"lambda_casa": 1.20, "lambda_ospite": 0.90},
    "catanzaro": {"lambda_casa": 1.25, "lambda_ospite": 0.95},
    "cesena": {"lambda_casa": 1.25, "lambda_ospite": 0.90},
    "pisa": {"lambda_casa": 1.30, "lambda_ospite": 1.00},
    "modena": {"lambda_casa": 1.15, "lambda_ospite": 0.85},
    "spezia": {"lambda_casa": 1.20, "lambda_ospite": 0.90},
    "juve stabia": {"lambda_casa": 1.15, "lambda_ospite": 0.80},
    "mantova": {"lambda_casa": 1.20, "lambda_ospite": 0.85},
    "reggiana": {"lambda_casa": 1.10, "lambda_ospite": 0.80},
    "sudtirol": {"lambda_casa": 1.10, "lambda_ospite": 0.80},
    "cosenza": {"lambda_casa": 1.05, "lambda_ospite": 0.75},
    "cittadella": {"lambda_casa": 1.05, "lambda_ospite": 0.75},
    "carrarese": {"lambda_casa": 1.00, "lambda_ospite": 0.70},

    # PREMIER LEAGUE
    "manchester city": {"lambda_casa": 2.60, "lambda_ospite": 2.00},
    "arsenal": {"lambda_casa": 2.30, "lambda_ospite": 1.80},
    "liverpool": {"lambda_casa": 2.40, "lambda_ospite": 1.85},
    "chelsea": {"lambda_casa": 1.90, "lambda_ospite": 1.45},
    "tottenham": {"lambda_casa": 2.00, "lambda_ospite": 1.50},
    "manchester united": {"lambda_casa": 1.75, "lambda_ospite": 1.30},
    "aston villa": {"lambda_casa": 1.85, "lambda_ospite": 1.40},
    "newcastle": {"lambda_casa": 1.95, "lambda_ospite": 1.35},
    "brighton": {"lambda_casa": 1.60, "lambda_ospite": 1.25},
    "west ham": {"lambda_casa": 1.50, "lambda_ospite": 1.15},

    # LA LIGA
    "real madrid": {"lambda_casa": 2.40, "lambda_ospite": 1.90},
    "barcellona": {"lambda_casa": 2.50, "lambda_ospite": 1.85},
    "atletico madrid": {"lambda_casa": 1.90, "lambda_ospite": 1.40},
    "athletic bilbao": {"lambda_casa": 1.70, "lambda_ospite": 1.20},
    "girona": {"lambda_casa": 1.80, "lambda_ospite": 1.30},
    "real sociedad": {"lambda_casa": 1.55, "lambda_ospite": 1.15},
    "villarreal": {"lambda_casa": 1.65, "lambda_ospite": 1.25},
    "real betis": {"lambda_casa": 1.50, "lambda_ospite": 1.10},

    # BUNDESLIGA
    "bayern monaco": {"lambda_casa": 2.55, "lambda_ospite": 1.95},
    "bayer leverkusen": {"lambda_casa": 2.35, "lambda_ospite": 1.85},
    "borussia": {"lambda_casa": 2.15, "lambda_ospite": 1.55},
    "lipsia": {"lambda_casa": 2.05, "lambda_ospite": 1.50},
    "stoccarda": {"lambda_casa": 2.00, "lambda_ospite": 1.45},
    "eintracht francoforte": {"lambda_casa": 1.75, "lambda_ospite": 1.30},

    # LIGUE 1
    "psg": {"lambda_casa": 2.50, "lambda_ospite": 2.00},
    "marseille": {"lambda_casa": 1.85, "lambda_ospite": 1.35},
    "monaco": {"lambda_casa": 1.90, "lambda_ospite": 1.40},
    "lyon": {"lambda_casa": 1.70, "lambda_ospite": 1.25},
    "lille": {"lambda_casa": 1.75, "lambda_ospite": 1.20},
    "lens": {"lambda_casa": 1.60, "lambda_ospite": 1.15}
}

# 4. DATABASE SEVERITÀ ARBITRI
DB_ARBITRI = {
    "default": 5,
    "davide massa": 10, "gianluca aureliano": 10, "benjamin brand": 10, "frank willenborg": 10,
    "mateo busquets ferrer": 10, "willie delajod": 10, "paul tierney": 10, "fabio maresca": 9,
    "giuseppe collu": 9, "ivano pezzuto": 9, "davide di marco": 9, "florian exner": 9,
    "gil manzano": 9, "hernandez hernandez": 9, "cesar soto grado": 9, "jeremie pignard": 9,
    "bastien dechepy": 9, "simon hooper": 9, "darren england": 9, "francesco fourneau": 8,
    "matteo marcenaro": 8, "michael fabbri": 8, "matteo gualtieri": 8, "paride tremolada": 8,
    "daniel siebert": 8, "matthias jöllenbeck": 8, "martinez munuera": 8, "alberola rojas": 8,
    "francois letexier": 8, "benoit bastien": 8, "michael oliver": 8, "anthony taylor": 8,
    "marco guida": 7, "maurizio mariani": 7, "giovanni ayroldi": 7, "alberto ruben arena": 7,
    "gianluca manganiello": 7, "simone galipò": 7, "tobias welz": 7, "daniel schlager": 7,
    "sanchez martinez": 7, "muniz ruiz": 7, "garcia verdura": 7, "ruddy buquet": 7,
    "jeremy stinat": 7, "eric wattellier": 7, "jarred gillett": 7, "david coote": 7,
    "craig pawson": 7, "federico la penna": 6, "rosario abisso": 6, "juan luca sacchi": 6,
    "andrea colombo": 6, "andrea zanotti": 6, "niccolò turrini": 6, "sören storks": 6,
    "patrick ittrich": 6, "munuera montero": 6, "cuadra fernandez": 6, "gomez ace": 6,
    "clement turpin": 6, "stéphanie frappart": 6, "florent batta": 6, "chris kavanagh": 6,
    "andy madley": 6, "tim robinson": 6, "giacomo camplone": 5, "matteo marchetti": 5,
    "simone sozza": 5, "daniele doveri": 5, "livio marinelli": 5, "felix zwayer": 5,
    "timo gerach": 5, "robin braun": 5, "de burgos bengoetxea": 5, "ortiz arias": 5,
    "maeso": 5, "mathieu vernice": 5, "gael angoula": 5, "robert jones": 5,
    "sam barrott": 5, "kevin bonacina": 4, "sven jablonski": 4, "florian badstübner": 4,
    "iglesias villanueva": 4, "figueroa vazquez": 4, "thomas leonard": 4, "benoit millot": 4,
    "john brooks": 4, "peter bankes": 4, "luca zufferli": 3, "daniele rutella": 3,
    "alessandro prontera": 3, "tobias stieler": 3, "sascha stegemann": 3, "harm osmers": 3,
    "pulido santana": 3, "garcia maeso": 3, "romain lissorgue": 3, "marc bollengier": 3,
    "tony harrington": 3, "michael salisbury": 3, "daniele perenzoni": 2, "ermanno feliciani": 2,
    "daniele chiffi": 2, "marco di bello": 2, "robert hartmann": 2, "deniz aytekin": 2,
    "ahmad heydari": 2, "stuart attwell": 2
}

# ==========================================
# 🔍 FUNZIONE SCRAPING ARBITRO LIVE & ND
# ==========================================
@timed_cache(seconds=60)
def scrappa_arbitro_live(squadra_casa: str, squadra_ospite: str) -> str:
    """
    Esegue lo scraping web per rilevare l'arbitro ufficiale designato per il match.
    Protetto da cache intelligente a 60 secondi.
    Se la designazione non è ancora disponibile o in caso di assenza/errore, restituisce tassativamente 'ND'.
    """
    try:
        url_ricerca = f"https://www.google.com/search?q=arbitro+designato+{squadra_casa}+{squadra_ospite}"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url_ricerca, headers=headers, timeout=3)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            pass
            
        return "ND"
    except Exception:
        return "ND"

def genera_contesto_match(casa: str, ospite: str):
    casa_key = normalizza_nome_squadra(casa)
    ospite_key = normalizza_nome_squadra(ospite)

    stadio_info = DB_STADI.get(casa_key, DB_STADI["default"])
    all_casa = DB_ALLENATORI.get(casa_key, DB_ALLENATORI["default"])
    all_ospite = DB_ALLENATORI.get(ospite_key, DB_ALLENATORI["default"])
    
    arbitro_designato = scrappa_arbitro_live(casa, ospite)
    
    if arbitro_designato == "ND":
        severita_arbitro = "ND"
    else:
        arb_key = arbitro_designato.lower().strip()
        severita_arbitro = DB_ARBITRI.get(arb_key, DB_ARBITRI["default"])
    
    meteo_live = ottieni_meteo_live(stadio_info.get("lat"), stadio_info.get("lon"))
    copertura_str = "Coperto" if stadio_info.get("coperto", False) else "Scoperto"
    
    return {
        "Stadio Casa": stadio_info.get("stadio", "N/D"),
        "Città": stadio_info.get("citta", "N/D"),
        "Terreno & Copertura": f"{stadio_info.get('campo', 'N/D')} - {copertura_str}",
        "Allenatore Casa": all_casa.get("allenatore", "N/D"),
        "Indice Tattico Casa": str(all_casa.get("indice_tattico", "N/D")),
        "Allenatore Ospite": all_ospite.get("allenatore", "N/D"),
        "Indice Tattico Ospite": str(all_ospite.get("indice_tattico", "N/D")),
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
    version="2.3.2"
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
        "version": "2.3.2",
        "principio": "Costruire, non Sostituire"
    }

@app.post("/analizza")
@app.post("/predict")
def analizza_partita(req: MatchRequest):
    casa = req.squadra_casa or req.home or "Casa"
    ospite = req.squadra_ospite or req.away or "Trasferta"
    match_id = req.match_id or f"{casa.lower()}_{ospite.lower()}"

    casa_key = normalizza_nome_squadra(casa)
    ospite_key = normalizza_nome_squadra(ospite)

    stats_casa = DB_LAMBDA_SQUADRE.get(casa_key, DB_LAMBDA_SQUADRE["default"])
    stats_ospite = DB_LAMBDA_SQUADRE.get(ospite_key, DB_LAMBDA_SQUADRE["default"])

    l_casa_base = req.lambda_casa if req.lambda_casa is not None else stats_casa["lambda_casa"]
    l_ospite_base = req.lambda_ospite if req.lambda_ospite is not None else stats_ospite["lambda_ospite"]

    # Esecuzione scraping arbitro live per la partita
    arbitro_designato = scrappa_arbitro_live(casa, ospite)

    # Gestione neutralizzazione: se l'arbitro è "ND" o non esplicitamente forzato, il moltiplicatore è 1.0 neutro
    if arbitro_designato == "ND" or req.moltiplicatore_arbitro != 1.0:
        molt_arbitro = req.moltiplicatore_arbitro if req.moltiplicatore_arbitro != 1.0 else 1.0
    else:
        arb_key = arbitro_designato.lower().strip()
        sev = DB_ARBITRI.get(arb_key, DB_ARBITRI["default"])
        molt_arbitro = 1.0 + (sev - 5) * 0.02

    l_casa_adj = l_casa_base * req.moltiplicatore_infortuni * req.moltiplicatore_stadio
    l_ospite_adj = l_ospite_base * molt_arbitro
    
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
            "lambda_ospite_effettivo": round(l_ospite_adj, 2),
            "arbitro_rilevato": arbitro_designato,
            "moltiplicatore_arbitro_applicato": round(molt_arbitro, 2)
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
            "volume_normale": "€0"
        }
    }