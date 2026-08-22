import os
import math
import time
import sqlite3
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
    "ss juve stabia": "juve stabia",
    "genoa": "genova"
}

def normalizza_nome_squadra(nome: str) -> str:
    if not nome:
        return "default"
    clean = nome.strip().lower()
    return TEAM_ALIASES.get(clean, clean)

# ==========================================
# 🗄️ DATABASE PROPRIETARI COMPLETI & FALLBACK
# ==========================================
DEFAULT_STADIO = {"stadio": "Stadio Generico", "citta": "N/D", "campo": "non trovato", "lat": 0.0, "lon": 0.0, "media_cartellini": "N/D", "coperto": "N/D"}
DEFAULT_ALLENATORE = {"allenatore": "Non dichiarato", "indice_tattico": N.D.}
DEFAULT_LAMBDA = {"lambda_casa": N.D., "lambda_ospite": N.D.}

# Sostituisci con i tuoi database completi
DB_STADI = {
    "default": DEFAULT_STADIO,
     "atalanta": {"stadio": "Gewiss Stadium", "citta": "Bergamo", "campo": "erba_naturale", "lat": 45.71, "lon": 9.68, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "bologna": {"stadio": "Stadio Renato Dall'Ara", "citta": "Bologna", "campo": "erba_naturale", "lat": 44.49, "lon": 11.31, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "cagliari": {"stadio": "Unipol Domus", "citta": "Cagliari", "campo": "erba_naturale", "lat": 39.20, "lon": 9.13, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]
    "como": {"stadio": "Stadio Giuseppe Sinigaglia", "citta": "Como", "campo": "erba_naturale", "lat": 45.81, "lon": 9.07, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "empoli": {"stadio": "Stadio Carlo Castellani", "citta": "Empoli", "campo": "erba_naturale", "lat": 43.72, "lon": 10.95, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "fiorentina": {"stadio": "Stadio Artemio Franchi", "citta": "Firenze", "campo": "erba_naturale", "lat": 43.78, "lon": 11.28, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "genoa": {"stadio": "Stadio Luigi Ferraris", "citta": "Genova", "campo": "erba_naturale", "lat": 44.42, "lon": 8.95, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "hellas verona": {"stadio": "Stadio Marcantonio Bentegodi", "citta": "Verona", "campo": "erba_naturale", "lat": 45.43, "lon": 10.97, "media_cartellini": 2.6, "coperto": False}, #[cite: 1]
    "inter": {"stadio": "Stadio Giuseppe Meazza", "citta": "Milano", "campo": "erba_ibrida", "lat": 45.47, "lon": 9.12, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "juventus": {"stadio": "Allianz Stadium", "citta": "Torino", "campo": "erba_naturale", "lat": 45.10, "lon": 7.64, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "lazio": {"stadio": "Stadio Olimpico", "citta": "Roma", "campo": "erba_naturale", "lat": 41.93, "lon": 12.45, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]
    "lecce": {"stadio": "Stadio Via del Mare", "citta": "Lecce", "campo": "erba_naturale", "lat": 40.36, "lon": 18.18, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "milan": {"stadio": "Stadio Giuseppe Meazza", "citta": "Milano", "campo": "erba_ibrida", "lat": 45.47, "lon": 9.12, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "monza": {"stadio": "U-Power Stadium", "citta": "Monza", "campo": "erba_naturale", "lat": 45.58, "lon": 9.27, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "napoli": {"stadio": "Stadio Diego Armando Maradona", "citta": "Napoli", "campo": "erba_naturale", "lat": 40.82, "lon": 14.19, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "parma": {"stadio": "Stadio Ennio Tardini", "citta": "Parma", "campo": "erba_naturale", "lat": 44.79, "lon": 10.33, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "roma": {"stadio": "Stadio Olimpico", "citta": "Roma", "campo": "erba_naturale", "lat": 41.93, "lon": 12.45, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]
    "torino": {"stadio": "Stadio Olimpico Grande Torino", "citta": "Torino", "campo": "erba_naturale", "lat": 45.03, "lon": 7.65, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "udinese": {"stadio": "Bluenergy Stadium", "citta": "Udine", "campo": "erba_naturale", "lat": 46.06, "lon": 13.19, "media_cartellini": 2.6, "coperto": True}, #[cite: 1]
    "venezia": {"stadio": "Stadio Pier Luigi Penzo", "citta": "Venezia", "campo": "erba_naturale", "lat": 45.42, "lon": 12.36, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "frosinone": {"stadio": "Stadio Benito Stirpe", "citta": "Frosinone", "campo": "erba_naturale", "lat": 41.63, "lon": 13.34, "media_cartellini": 2.6, "coperto": False},    #[cite: 1]

 # BUNDESLIGA[cite: 1]
    "bayern munich": {"stadio": "Allianz Arena", "citta": "Munich", "campo": "erba_naturale", "lat": 48.21, "lon": 11.62, "media_cartellini": 1.8, "coperto": False}, #[cite: 1]
    "borussia dortmund": {"stadio": "Signal Iduna Park", "citta": "Dortmund", "campo": "erba_naturale", "lat": 51.49, "lon": 7.45, "media_cartellini": 2.0, "coperto": False}, #[cite: 1]
    "bayer leverkusen": {"stadio": "BayArena", "citta": "Leverkusen", "campo": "erba_naturale", "lat": 51.03, "lon": 7.00, "media_cartellini": 1.9, "coperto": False}, #[cite: 1]
    "rb leipzig": {"stadio": "Red Bull Arena", "citta": "Leipzig", "campo": "erba_naturale", "lat": 51.34, "lon": 12.34, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "eintracht frankfurt": {"stadio": "Deutsche Bank Park", "citta": "Frankfurt", "campo": "erba_naturale", "lat": 50.06, "lon": 8.64, "media_cartellini": 2.3, "coperto": True}, #[cite: 1]
    "vfl wolfsburg": {"stadio": "Volkswagen Arena", "citta": "Wolfsburg", "campo": "erba_naturale", "lat": 52.43, "lon": 10.80, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "borussia mgladbach": {"stadio": "Borussia-Park", "citta": "Monchengladbach", "campo": "erba_naturale", "lat": 51.16, "lon": 6.38, "media_cartellini": 2.0, "coperto": False}, #[cite: 1]
    "sc freiburg": {"stadio": "Europa-Park Stadion", "citta": "Freiburg", "campo": "erba_naturale", "lat": 48.01, "lon": 7.82, "media_cartellini": 1.9, "coperto": False}, #[cite: 1]
    "tsg hoffenheim": {"stadio": "PreZero Arena", "citta": "Sinsheim", "campo": "erba_naturale", "lat": 49.23, "lon": 8.87, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "vfb stuttgart": {"stadio": "MHPArena", "citta": "Stuttgart", "campo": "erba_naturale", "lat": 48.79, "lon": 9.23, "media_cartellini": 2.0, "coperto": False}, #[cite: 1]
    "werder bremen": {"stadio": "Wohninvest Weserstadion", "citta": "Bremen", "campo": "erba_naturale", "lat": 53.06, "lon": 8.83, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "fc augsburg": {"stadio": "WWK Arena", "citta": "Augsburg", "campo": "erba_naturale", "lat": 48.32, "lon": 10.88, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "mainz 05": {"stadio": "Mewa Arena", "citta": "Mainz", "campo": "erba_naturale", "lat": 49.98, "lon": 8.22, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "1. fc union berlin": {"stadio": "Stadion An der Alten Forsterei", "citta": "Berlin", "campo": "erba_naturale", "lat": 52.45, "lon": 13.56, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "fc st. pauli": {"stadio": "Millerntor-Stadion", "citta": "Hamburg", "campo": "erba_naturale", "lat": 53.55, "lon": 9.96, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "holstein kiel": {"stadio": "Holstein-Stadion", "citta": "Kiel", "campo": "erba_naturale", "lat": 54.34, "lon": 10.12, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "vfl bochum": {"stadio": "Vonovia Ruhrstadion", "citta": "Bochum", "campo": "erba_naturale", "lat": 51.48, "lon": 7.23, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "fc heidenheim": {"stadio": "Voith-Arena", "citta": "Heidenheim", "campo": "erba_naturale", "lat": 48.67, "lon": 10.16, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]

    # LA LIGA[cite: 1]
    "real madrid": {"stadio": "Santiago Bernabeu", "citta": "Madrid", "campo": "erba_ibrida", "lat": 40.45, "lon": -3.68, "media_cartellini": 1.9, "coperto": True}, #[cite: 1]
    "fc barcelona": {"stadio": "Estadi Olimpic Lluis Companys", "citta": "Barcelona", "campo": "erba_naturale", "lat": 41.36, "lon": 2.15, "media_cartellini": 2.0, "coperto": False}, #[cite: 1]
    "atletico madrid": {"stadio": "Metropolitano", "citta": "Madrid", "campo": "erba_naturale", "lat": 40.43, "lon": -3.59, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]
    "athletic club": {"stadio": "San Mames", "citta": "Bilbao", "campo": "erba_naturale", "lat": 43.26, "lon": -2.94, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "villarreal": {"stadio": "Estadio de la Ceramica", "citta": "Villarreal", "campo": "erba_naturale", "lat": 39.94, "lon": -0.10, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "real sociedad": {"stadio": "Reale Arena", "citta": "San Sebastian", "campo": "erba_naturale", "lat": 43.30, "lon": -1.97, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "real betis": {"stadio": "Benito Villamarin", "citta": "Seville", "campo": "erba_naturale", "lat": 37.35, "lon": -5.98, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "sevilla": {"stadio": "Ramon Sanchez-Pizjuan", "citta": "Seville", "campo": "erba_naturale", "lat": 37.38, "lon": -5.97, "media_cartellini": 2.6, "coperto": False}, #[cite: 1]
    "girona": {"stadio": "Montilivi", "citta": "Girona", "campo": "erba_naturale", "lat": 41.96, "lon": 2.82, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "valencia": {"stadio": "Mestalla", "citta": "Valencia", "campo": "erba_naturale", "lat": 39.47, "lon": -0.35, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]
    "osasuna": {"stadio": "El Sadar", "citta": "Pamplona", "campo": "erba_naturale", "lat": 42.79, "lon": -1.63, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "celta vigo": {"stadio": "Abanca-Balaidos", "citta": "Vigo", "campo": "erba_naturale", "lat": 42.21, "lon": -8.74, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "getafe": {"stadio": "Coliseum", "citta": "Getafe", "campo": "erba_naturale", "lat": 40.32, "lon": -3.72, "media_cartellini": 3.0, "coperto": False}, #[cite: 1]
    "mallorca": {"stadio": "Son Moix", "citta": "Palma", "campo": "erba_naturale", "lat": 39.59, "lon": 2.62, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "alaves": {"stadio": "Mendizorrotza", "citta": "Vitoria-Gasteiz", "campo": "erba_naturale", "lat": 42.84, "lon": -2.68, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "rayo vallecano": {"stadio": "Campo de Vallecas", "citta": "Madrid", "campo": "erba_naturale", "lat": 40.39, "lon": -3.65, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]
    "las palmas": {"stadio": "Gran Canaria", "citta": "Las Palmas", "campo": "erba_naturale", "lat": 28.10, "lon": -15.45, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "espanyol": {"stadio": "Stage Front Stadium", "citta": "Barcelona", "campo": "erba_naturale", "lat": 41.34, "lon": 2.07, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "real valladolid": {"stadio": "Jose Zorrilla", "citta": "Valladolid", "campo": "erba_naturale", "lat": 41.65, "lon": -4.75, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "leganes": {"stadio": "Butarque", "citta": "Leganes", "campo": "erba_naturale", "lat": 40.33, "lon": -3.76, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]

    # LIGUE 1[cite: 1]
    "paris saint-germain": {"stadio": "Parc des Princes", "citta": "Paris", "campo": "erba_ibrida", "lat": 48.84, "lon": 2.25, "media_cartellini": 1.7, "coperto": False}, #[cite: 1]
    "olympique lyonnais": {"stadio": "Groupama Stadium", "citta": "Lyon", "campo": "erba_ibrida", "lat": 45.76, "lon": 4.97, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "olympique marseille": {"stadio": "Stade Velodrome", "citta": "Marseille", "campo": "erba_naturale", "lat": 43.26, "lon": 5.39, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "as monaco": {"stadio": "Stade Louis II", "citta": "Monaco", "campo": "erba_naturale", "lat": 43.72, "lon": 7.41, "media_cartellini": 1.9, "coperto": False}, #[cite: 1]
    "lille": {"stadio": "Stade Pierre-Mauroy", "citta": "Lille", "campo": "erba_ibrida", "lat": 50.61, "lon": 3.13, "media_cartellini": 2.2, "coperto": True}, #[cite: 1]
    "nice": {"stadio": "Allianz Riviera", "citta": "Nice", "campo": "erba_ibrida", "lat": 43.71, "lon": 7.18, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "lens": {"stadio": "Stade Bollaert-Delelis", "citta": "Lens", "campo": "erba_naturale", "lat": 50.43, "lon": 2.82, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "rennes": {"stadio": "Roazhon Park", "citta": "Rennes", "campo": "erba_naturale", "lat": 48.10, "lon": -1.71, "media_cartellini": 2.0, "coperto": False}, #[cite: 1]
    "stade de reims": {"stadio": "Stade Auguste-Delaune", "citta": "Reims", "campo": "erba_naturale", "lat": 49.24, "lon": 4.02, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "strasbourg": {"stadio": "Stade de la Meinau", "citta": "Strasbourg", "campo": "erba_naturale", "lat": 48.56, "lon": 7.75, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "toulouse": {"stadio": "Stadium de Toulouse", "citta": "Toulouse", "campo": "erba_naturale", "lat": 43.58, "lon": 1.43, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "nantes": {"stadio": "Stade de la Beaujoire", "citta": "Nantes", "campo": "erba_naturale", "lat": 47.25, "lon": -1.52, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "montpellier": {"stadio": "Stade de la Mosson", "citta": "Montpellier", "campo": "erba_naturale", "lat": 43.62, "lon": 3.81, "media_cartellini": 2.6, "coperto": False}, #[cite: 1]
    "le havre": {"stadio": "Stade Oceane", "citta": "Le Havre", "campo": "erba_naturale", "lat": 49.50, "lon": 0.17, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]
    "auxerre": {"stadio": "Stade de l'Abbe-Deschamps", "citta": "Auxerre", "campo": "erba_naturale", "lat": 47.77, "lon": 3.58, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "saint-etienne": {"stadio": "Stade Geoffroy-Guichard", "citta": "Saint-Etienne", "campo": "erba_naturale", "lat": 45.45, "lon": 4.39, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]
    "angers": {"stadio": "Stade Raymond Kopa", "citta": "Angers", "campo": "erba_naturale", "lat": 47.47, "lon": -0.55, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "brest": {"stadio": "Stade Francis-Le Ble", "citta": "Brest", "campo": "erba_naturale", "lat": 48.40, "lon": -4.49, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]

    # PREMIER LEAGUE[cite: 1]
    "arsenal": {"stadio": "Emirates Stadium", "citta": "London", "campo": "erba_naturale", "lat": 51.55, "lon": -0.10, "media_cartellini": 1.9, "coperto": False}, #[cite: 1]
    "aston villa": {"stadio": "Villa Park", "citta": "Birmingham", "campo": "erba_naturale", "lat": 52.50, "lon": -1.88, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "bournemouth": {"stadio": "Vitality Stadium", "citta": "Bournemouth", "campo": "erba_naturale", "lat": 50.73, "lon": -1.83, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "brentford": {"stadio": "Gtech Community Stadium", "citta": "London", "campo": "erba_naturale", "lat": 51.48, "lon": -0.28, "media_cartellini": 2.0, "coperto": False}, #[cite: 1]
    "brighton": {"stadio": "Amex Stadium", "citta": "Brighton", "campo": "erba_naturale", "lat": 50.86, "lon": -0.08, "media_cartellini": 2.0, "coperto": False}, #[cite: 1]
    "chelsea": {"stadio": "Stamford Bridge", "citta": "London", "campo": "erba_naturale", "lat": 51.48, "lon": -0.19, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "crystal palace": {"stadio": "Selhurst Park", "citta": "London", "campo": "erba_naturale", "lat": 51.39, "lon": -0.08, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "everton": {"stadio": "Goodison Park", "citta": "Liverpool", "campo": "erba_naturale", "lat": 53.44, "lon": -2.96, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]
    "fulham": {"stadio": "Craven Cottage", "citta": "London", "campo": "erba_naturale", "lat": 51.47, "lon": -0.22, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "ipswich town": {"stadio": "Portman Road", "citta": "Ipswich", "campo": "erba_naturale", "lat": 52.05, "lon": 1.14, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "leicester city": {"stadio": "King Power Stadium", "citta": "Leicester", "campo": "erba_naturale", "lat": 52.62, "lon": -1.14, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "liverpool": {"stadio": "Anfield", "citta": "Liverpool", "campo": "erba_naturale", "lat": 53.43, "lon": -2.96, "media_cartellini": 1.8, "coperto": False}, #[cite: 1]
    "manchester city": {"stadio": "Etihad Stadium", "citta": "Manchester", "campo": "erba_ibrida", "lat": 53.48, "lon": -2.20, "media_cartellini": 1.7, "coperto": False}, #[cite: 1]
    "manchester united": {"stadio": "Old Trafford", "citta": "Manchester", "campo": "erba_naturale", "lat": 53.46, "lon": -2.29, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "newcastle united": {"stadio": "St. James' Park", "citta": "Newcastle", "campo": "erba_naturale", "lat": 54.97, "lon": -1.62, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "nottingham forest": {"stadio": "City Ground", "citta": "Nottingham", "campo": "erba_naturale", "lat": 52.93, "lon": -1.13, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "southampton": {"stadio": "St Mary's Stadium", "citta": "Southampton", "campo": "erba_naturale", "lat": 50.90, "lon": -1.39, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "tottenham": {"stadio": "Tottenham Hotspur Stadium", "citta": "London", "campo": "erba_naturale", "lat": 51.60, "lon": -0.06, "media_cartellini": 2.3, "coperto": True}, #[cite: 1]
    "west ham": {"stadio": "London Stadium", "citta": "London", "campo": "erba_naturale", "lat": 51.53, "lon": -0.01, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "wolverhampton": {"stadio": "Molineux Stadium", "citta": "Wolverhampton", "campo": "erba_naturale", "lat": 52.59, "lon": -2.13, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]

    # SERIE B[cite: 1]
    "bari": {"stadio": "Stadio San Nicola", "citta": "Bari", "campo": "erba_naturale", "lat": 41.08, "lon": 16.82, "media_cartellini": 2.7, "coperto": False}, #[cite: 1]
    "brescia": {"stadio": "Stadio Mario Rigamonti", "citta": "Brescia", "campo": "erba_naturale", "lat": 45.56, "lon": 10.23, "media_cartellini": 2.6, "coperto": False}, #[cite: 1]
    "carrarese": {"stadio": "Stadio dei Marmi", "citta": "Carrara", "campo": "erba_naturale", "lat": 44.07, "lon": 10.08, "media_cartellini": 2.8, "coperto": False}, #[cite: 1]
    "cesena": {"stadio": "Orogel Stadium-Dino Manuzzi", "citta": "Cesena", "campo": "erba_naturale", "lat": 44.13, "lon": 12.24, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]
    "cittadella": {"stadio": "Stadio Piercesare Tombolato", "citta": "Cittadella", "campo": "erba_naturale", "lat": 45.64, "lon": 11.78, "media_cartellini": 2.7, "coperto": False}, #[cite: 1]
    "cosenza": {"stadio": "Stadio San Vito-Gigi Marulla", "citta": "Cosenza", "campo": "erba_naturale", "lat": 39.31, "lon": 16.25, "media_cartellini": 2.8, "coperto": False}, #[cite: 1]
    "cremonese": {"stadio": "Stadio Giovanni Zini", "citta": "Cremona", "campo": "erba_naturale", "lat": 45.13, "lon": 10.03, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "juve stabia": {"stadio": "Stadio Romeo Menti", "citta": "Castellammare di Stabia", "campo": "erba_naturale", "lat": 40.70, "lon": 14.48, "media_cartellini": 2.7, "coperto": False}, #[cite: 1]
    "mantova": {"stadio": "Stadio Danilo Martelli", "citta": "Mantova", "campo": "erba_naturale", "lat": 45.16, "lon": 10.79, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]
    "modena": {"stadio": "Stadio Alberto Braglia", "citta": "Modena", "campo": "erba_naturale", "lat": 44.65, "lon": 10.92, "media_cartellini": 2.6, "coperto": False}, #[cite: 1]
    "palermo": {"stadio": "Stadio Renzo Barbera", "citta": "Palermo", "campo": "erba_naturale", "lat": 38.15, "lon": 13.34, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "pisa": {"stadio": "Stadio Arena Garibaldi", "citta": "Pisa", "campo": "erba_naturale", "lat": 43.72, "lon": 10.40, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]
    "reggiana": {"stadio": "Mapei Stadium", "citta": "Reggio Emilia", "campo": "erba_naturale", "lat": 44.71, "lon": 10.64, "media_cartellini": 2.6, "coperto": False}, #[cite: 1]
    "salernitana": {"stadio": "Stadio Arechi", "citta": "Salerno", "campo": "erba_naturale", "lat": 40.66, "lon": 14.82, "media_cartellini": 2.7, "coperto": False}, #[cite: 1]
    "sampdoria": {"stadio": "Stadio Luigi Ferraris", "citta": "Genova", "campo": "erba_naturale", "lat": 44.42, "lon": 8.95, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "sassuolo": {"stadio": "Mapei Stadium", "citta": "Reggio Emilia", "campo": "erba_naturale", "lat": 44.71, "lon": 10.64, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "spezia": {"stadio": "Stadio Alberto Picco", "citta": "La Spezia", "campo": "erba_naturale", "lat": 44.10, "lon": 9.82, "media_cartellini": 2.5, "coperto": False}, #[cite: 1]
    "sudtirol": {"stadio": "Stadio Druso", "citta": "Bolzano", "campo": "erba_naturale", "lat": 46.49, "lon": 11.34, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "catanzaro": {"stadio": "Stadio Nicola Ceravolo", "citta": "Catanzaro", "campo": "erba_naturale", "lat": 38.89, "lon": 16.59, "media_cartellini": 2.6, "coperto": False}, #[cite: 1]

    # NAZIONALI[cite: 1]
    "italy": {"stadio": "Stadio Olimpico", "citta": "Roma", "campo": "erba_naturale", "lat": 41.93, "lon": 12.45, "media_cartellini": 2.2, "coperto": False}, #[cite: 1]
    "germany": {"stadio": "Olympiastadion", "citta": "Berlin", "campo": "erba_naturale", "lat": 52.51, "lon": 13.24, "media_cartellini": 1.8, "coperto": False}, #[cite: 1]
    "france": {"stadio": "Stade de France", "citta": "Saint-Denis", "campo": "erba_naturale", "lat": 48.92, "lon": 2.36, "media_cartellini": 1.9, "coperto": False}, #[cite: 1]
    "spain": {"stadio": "Santiago Bernabeu", "citta": "Madrid", "campo": "erba_ibrida", "lat": 40.45, "lon": -3.68, "media_cartellini": 1.7, "coperto": True}, #[cite: 1]
    "england": {"stadio": "Wembley Stadium", "citta": "London", "campo": "erba_naturale", "lat": 51.55, "lon": -0.27, "media_cartellini": 1.8, "coperto": True}, #[cite: 1]
    "brazil": {"stadio": "Maracana", "citta": "Rio de Janeiro", "campo": "erba_naturale", "lat": -22.91, "lon": -43.23, "media_cartellini": 2.6, "coperto": False}, #[cite: 1]
    "argentina": {"stadio": "Estadio Monumental", "citta": "Buenos Aires", "campo": "erba_naturale", "lat": -34.54, "lon": -58.45, "media_cartellini": 2.4, "coperto": False}, #[cite: 1]
    "portugal": {"stadio": "Estadio da Luz", "citta": "Lisbon", "campo": "erba_naturale", "lat": 38.75, "lon": -9.18, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "netherlands": {"stadio": "Johan Cruyff Arena", "citta": "Amsterdam", "campo": "erba_ibrida", "lat": 52.31, "lon": 4.94, "media_cartellini": 2.0, "coperto": True}, #[cite: 1]
    "belgium": {"stadio": "Stade Roi Baudouin", "citta": "Brussels", "campo": "erba_naturale", "lat": 50.89, "lon": 4.33, "media_cartellini": 2.1, "coperto": False}, #[cite: 1]
    "croatia": {"stadio": "Stadion Maksimir", "citta": "Zagreb", "campo": "erba_naturale", "lat": 45.81, "lon": 16.02, "media_cartellini": 2.3, "coperto": False}, #[cite: 1]
    "uruguay": {"stadio": "Estadio Centenario", "citta": "Montevideo", "campo": "erba_naturale", "lat": -34.89, "lon": -56.15, "media_cartellini": 2.8, "coperto": False} #[cite: 1]
}


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
DB_LAMBDA_SQUADRE = {
    "default": DEFAULT_LAMBDA,
    "inter": {"lambda_casa": 2.10, "lambda_ospite": 1.75},
    "atalanta": {"lambda_casa": 2.00, "lambda_ospite": 1.60},
}

DB_ARBITRI = {
    # SEVERISSIMI (Indice 9-10)
    "davide massa": 10,
    "gianluca aureliano": 10,
    "benjamin brand": 10,
    "frank willenborg": 10,
    "mateo busquets ferrer": 10,
    "willie delajod": 10,
    "paul tierney": 10,
    "fabio maresca": 9,
    "giuseppe collu": 9,
    "ivano pezzuto": 9,
    "davide di marco": 9,
    "florian exner": 9,
    "gil manzano": 9,
    "hernandez hernandez": 9,
    "cesar soto grado": 9,
    "jeremie pignard": 9,
    "bastien dechepy": 9,
    "simon hooper": 9,
    "darren england": 9,

    # SEVERI (Indice 7-8)
    "francesco fourneau": 8,
    "matteo marcenaro": 8,
    "michael fabbri": 8,
    "matteo gualtieri": 8,
    "paride tremolada": 8,
    "daniel siebert": 8,
    "matthias jöllenbeck": 8,
    "martinez munuera": 8,
    "alberola rojas": 8,
    "francois letexier": 8,
    "benoit bastien": 8,
    "michael oliver": 8,
    "anthony taylor": 8,
    "marco guida": 7,
    "maurizio mariani": 7,
    "giovanni ayroldi": 7,
    "alberto ruben arena": 7,
    "gianluca manganiello": 7,
    "simone galipò": 7,
    "tobias welz": 7,
    "daniel schlager": 7,
    "sanchez martinez": 7,
    "muniz ruiz": 7,
    "garcia verdura": 7,
    "ruddy buquet": 7,
    "jeremy stinat": 7,
    "eric wattellier": 7,
    "jarred gillett": 7,
    "david coote": 7,
    "craig pawson": 7,

    # MEDI (Indice 5-6)
    "federico la penna": 6,
    "rosario abisso": 6,
    "juan luca sacchi": 6,
    "andrea colombo": 6,
    "andrea zanotti": 6,
    "niccolò turrini": 6,
    "sören storks": 6,
    "patrick ittrich": 6,
    "munuera montero": 6,
    "cuadra fernandez": 6,
    "gomez ace": 6,
    "clement turpin": 6,
    "stéphanie frappart": 6,
    "florent batta": 6,
    "chris kavanagh": 6,
    "andy madley": 6,
    "tim robinson": 6,
    "giacomo camplone": 5,
    "matteo marchetti": 5,
    "simone sozza": 5,
    "daniele doveri": 5,
    "livio marinelli": 5,
    "felix zwayer": 5,
    "timo gerach": 5,
    "robin braun": 5,
    "de burgos bengoetxea": 5,
    "ortiz arias": 5,
    "maeso": 5,
    "mathieu vernice": 5,
    "gael angoula": 5,
    "robert jones": 5,
    "sam barrott": 5,

    # PERMISSIVI (Indice 1-4)
    "kevin bonacina": 4,
    "sven jablonski": 4,
    "florian badstübner": 4,
    "iglesias villanueva": 4,
    "figueroa vazquez": 4,
    "thomas leonard": 4,
    "benoit millot": 4,
    "john brooks": 4,
    "peter bankes": 4,
    "luca zufferli": 3,
    "daniele rutella": 3,
    "alessandro prontera": 3,
    "tobias stieler": 3,
    "sascha stegemann": 3,
    "harm osmers": 3,
    "pulido santana": 3,
    "garcia maeso": 3,
    "romain lissorgue": 3,
    "marc bollengier": 3,
    "tony harrington": 3,
    "michael salisbury": 3,
    "daniele perenzoni": 2,
    "ermanno feliciani": 2,
    "daniele chiffi": 2,
    "marco di bello": 2,
    "robert hartmann": 2,
    "deniz aytekin": 2,
    "ahmad heydari": 2,
    "stuart attwell": 2
}
# ==========================================
# 🔍 FUNZIONE SCRAPING ARBITRO LIVE & ND
# ==========================================
@timed_cache(seconds=60)
def scrappa_arbitro_live(squadra_casa: str, squadra_ospite: str) -> str:
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
        "Meteo Live": meteo_live,
        "Media Cartellini Stadio": stadio_info.get("media_cartellini", 2.0)
    }

# ==========================================
# 🧠 MASTER CALCULATOR (INTEGRAZIONE REALE)
# ==========================================
def ottieni_flussi_monetari_reali(casa: str, ospite: str) -> dict:
    """
    Spazio dedicato alla VERA chiamata API (o query al DB) per i volumi di mercato.
    In assenza del feed dati, ritorna lo stato di attesa senza simulare nulla.
    """
    # TODO: Inserire logica di fetch da API esterna/DB (Exchange, AsianOdds, ecc.)
    return {
        "flusso_str": "Feed flussi monetari reali non ancora collegato.",
        "whale_active": False
    }

def esegui_master_calculator(casa: str, ospite: str, contesto: dict):
    """
    Fonde trend storici, fattori umani, fattori disciplinari e flussi monetari reali.
    """
    # 1. Tattica & Fattori Umani
    idx_casa = int(contesto.get("Indice Tattico Casa") if contesto.get("Indice Tattico Casa") != "N/D" else 5)
    idx_ospite = int(contesto.get("Indice Tattico Ospite") if contesto.get("Indice Tattico Ospite") != "N/D" else 5)
    vantaggio_tattico = "Equilibrio"
    
    if idx_casa > idx_ospite + 1:
        vantaggio_tattico = f"Vantaggio Tattico Casa ({contesto.get('Allenatore Casa')})"
    elif idx_ospite > idx_casa + 1:
        vantaggio_tattico = f"Vantaggio Tattico Ospite ({contesto.get('Allenatore Ospite')})"
    
    # 2. Rischio Disciplinare
    sev_arbitro = contesto.get("Severità Arbitro")
    media_stadio = contesto.get("Media Cartellini Stadio", 2.0)
    rischio_cartellini = "Basso"
    
    if sev_arbitro != "ND":
        if sev_arbitro >= 8 and media_stadio > 2.4:
            rischio_cartellini = "Critico (Alta probabilità Rossi/Rigori)"
        elif sev_arbitro >= 6:
            rischio_cartellini = "Moderato"
            
    # 3. Flussi Monetari (REALI)
    dati_flussi = ottieni_flussi_monetari_reali(casa, ospite)
    flusso_str = dati_flussi["flusso_str"]
    whale_active = dati_flussi["whale_active"]

    # 4. Trend Storici (Momentum Reale)
    # TODO: Integrare query al DB storico reale degli H2H
    momentum = "Dati H2H in attesa di fetch dal database storico."

    return {
        "fattori_umani": vantaggio_tattico,
        "disciplinare": rischio_cartellini,
        "flussi_monetari": flusso_str,
        "whale_alert": whale_active,
        "trend_storici": momentum
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

class CalcolaMatchRequest(BaseModel):
    home: str
    away: str
    date: Optional[str] = None

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

    arbitro_designato = scrappa_arbitro_live(casa, ospite)

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
    
    master_stats = esegui_master_calculator(casa, ospite, contesto_match)
    
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
        "master_calculator": master_stats, 
        "modulo_esperti": {
            "disponibile": len(dati_esperti) > 0,
            "totale_esperti": len(dati_esperti),
            "lista_esperti": dati_esperti
        },
        "whale_alert": {
            "attivo": master_stats["whale_alert"],
            "volume_effettivo": "€ND", 
            "volume_normale": "€ND"
        }
    }

# ==========================================
# 🚀 COMUNICAZIONE APP FLUTTER / DB ESPERTI
# ==========================================
def get_db_connection():
    conn = sqlite3.connect('esperti.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.post("/api/calcola-match")
def calcola_match(req: CalcolaMatchRequest):
    home_team = req.home
    away_team = req.away
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT * FROM pronostici WHERE squadra_casa = ? AND squadra_trasferta = ?",
                (home_team, away_team)
            )
            risultato_db = cursor.fetchone()
        except sqlite3.OperationalError:
            risultato_db = None
            
        panel_testo = "Nessun pronostico specifico trovato nel database per questo match. L'algoritmo calcolerà i dati puri."
        if risultato_db and 'pronostico' in risultato_db.keys():
            panel_testo = f"Il Veggente consiglia: {risultato_db['pronostico']}"
            
        conn.close()

        contesto = genera_contesto_match(home_team, away_team)
        master_stats = esegui_master_calculator(home_team, away_team, contesto)
        
        intelligence_risposta = {
            'mister': f"Tattica Casa: {contesto['Indice Tattico Casa']} | Tattica Ospite: {contesto['Indice Tattico Ospite']} -> {master_stats['fattori_umani']}",
            'arbitro': f"Designato: {contesto['Arbitro Designato']} (Severità: {contesto['Severità Arbitro']}) -> Rischio: {master_stats['disciplinare']}",
            'infortunati': 'Scansione API infortuni in corso...',
            'stadium': f"Stadio: {contesto['Stadio Casa']} ({contesto['Terreno & Copertura']}) - Meteo: {contesto['Meteo Live']}",
            'flussi': master_stats['flussi_monetari'],
            'storico': master_stats['trend_storici']
        }

        return {
            'panel_esperti': panel_testo,
            'intelligence': intelligence_risposta
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))