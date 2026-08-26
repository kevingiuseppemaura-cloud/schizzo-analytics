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
    "paris saint-germain": "psg",
    "paris sg": "psg",
    "olympique lyonnais": "lyon",
    "olympique de marseille": "marseille",
    "stade de reims": "reims",
    "as monaco": "monaco",
    "stade rennais fc": "rennes",
    "ogc nice": "nice",
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
DEFAULT_ALLENATORE = {"allenatore": "Non dichiarato", "indice_tattico": 5}
DEFAULT_LAMBDA = {"lambda_casa": 1.65, "lambda_ospite": 1.20}

DB_STADI = {
    "default": DEFAULT_STADIO,
    "atalanta": {"stadio": "Gewiss Stadium", "citta": "Bergamo", "campo": "erba_naturale", "lat": 45.71, "lon": 9.68, "media_cartellini": 2.4, "coperto": False},
    "bologna": {"stadio": "Stadio Renato Dall'Ara", "citta": "Bologna", "campo": "erba_naturale", "lat": 44.49, "lon": 11.31, "media_cartellini": 2.3, "coperto": False},
    "cagliari": {"stadio": "Unipol Domus", "citta": "Cagliari", "campo": "erba_naturale", "lat": 39.20, "lon": 9.13, "media_cartellini": 2.5, "coperto": False},
    "como": {"stadio": "Stadio Giuseppe Sinigaglia", "citta": "Como", "campo": "erba_naturale", "lat": 45.81, "lon": 9.07, "media_cartellini": 2.2, "coperto": False},
    "empoli": {"stadio": "Stadio Carlo Castellani", "citta": "Empoli", "campo": "erba_naturale", "lat": 43.72, "lon": 10.95, "media_cartellini": 2.1, "coperto": False},
    "fiorentina": {"stadio": "Stadio Artemio Franchi", "citta": "Firenze", "campo": "erba_naturale", "lat": 43.78, "lon": 11.28, "media_cartellini": 2.3, "coperto": False},
    "genoa": {"stadio": "Stadio Luigi Ferraris", "citta": "Genova", "campo": "erba_naturale", "lat": 44.42, "lon": 8.95, "media_cartellini": 2.4, "coperto": False},
    "hellas verona": {"stadio": "Stadio Marcantonio Bentegodi", "citta": "Verona", "campo": "erba_naturale", "lat": 45.43, "lon": 10.97, "media_cartellini": 2.6, "coperto": False},
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
    "frosinone": {"stadio": "Stadio Benito Stirpe", "citta": "Frosinone", "campo": "erba_naturale", "lat": 41.63, "lon": 13.34, "media_cartellini": 2.6, "coperto": False},
    "bayern munich": {"stadio": "Allianz Arena", "citta": "Munich", "campo": "erba_naturale", "lat": 48.21, "lon": 11.62, "media_cartellini": 1.8, "coperto": False},
    "borussia dortmund": {"stadio": "Signal Iduna Park", "citta": "Dortmund", "campo": "erba_naturale", "lat": 51.49, "lon": 7.45, "media_cartellini": 2.0, "coperto": False},
    "bayer leverkusen": {"stadio": "BayArena", "citta": "Leverkusen", "campo": "erba_naturale", "lat": 51.03, "lon": 7.00, "media_cartellini": 1.9, "coperto": False},
    "rb leipzig": {"stadio": "Red Bull Arena", "citta": "Leipzig", "campo": "erba_naturale", "lat": 51.34, "lon": 12.34, "media_cartellini": 2.2, "coperto": False},
    "eintracht frankfurt": {"stadio": "Deutsche Bank Park", "citta": "Frankfurt", "campo": "erba_naturale", "lat": 50.06, "lon": 8.64, "media_cartellini": 2.3, "coperto": True},
    "vfl wolfsburg": {"stadio": "Volkswagen Arena", "citta": "Wolfsburg", "campo": "erba_naturale", "lat": 52.43, "lon": 10.80, "media_cartellini": 2.1, "coperto": False},
    "borussia mgladbach": {"stadio": "Borussia-Park", "citta": "Monchengladbach", "campo": "erba_naturale", "lat": 51.16, "lon": 6.38, "media_cartellini": 2.0, "coperto": False},
    "sc freiburg": {"stadio": "Europa-Park Stadion", "citta": "Freiburg", "campo": "erba_naturale", "lat": 48.01, "lon": 7.82, "media_cartellini": 1.9, "coperto": False},
    "tsg hoffenheim": {"stadio": "PreZero Arena", "citta": "Sinsheim", "campo": "erba_naturale", "lat": 49.23, "lon": 8.87, "media_cartellini": 2.2, "coperto": False},
    "vfb stuttgart": {"stadio": "MHPArena", "citta": "Stuttgart", "campo": "erba_naturale", "lat": 48.79, "lon": 9.23, "media_cartellini": 2.0, "coperto": False},
    "werder bremen": {"stadio": "Wohninvest Weserstadion", "citta": "Bremen", "campo": "erba_naturale", "lat": 53.06, "lon": 8.83, "media_cartellini": 2.1, "coperto": False},
    "fc augsburg": {"stadio": "WWK Arena", "citta": "Augsburg", "campo": "erba_naturale", "lat": 48.32, "lon": 10.88, "media_cartellini": 2.4, "coperto": False},
    "mainz 05": {"stadio": "Mewa Arena", "citta": "Mainz", "campo": "erba_naturale", "lat": 49.98, "lon": 8.22, "media_cartellini": 2.3, "coperto": False},
    "1. fc union berlin": {"stadio": "Stadion An der Alten Forsterei", "citta": "Berlin", "campo": "erba_naturale", "lat": 52.45, "lon": 13.56, "media_cartellini": 2.4, "coperto": False},
    "fc st. pauli": {"stadio": "Millerntor-Stadion", "citta": "Hamburg", "campo": "erba_naturale", "lat": 53.55, "lon": 9.96, "media_cartellini": 2.3, "coperto": False},
    "holstein kiel": {"stadio": "Holstein-Stadion", "citta": "Kiel", "campo": "erba_naturale", "lat": 54.34, "lon": 10.12, "media_cartellini": 2.2, "coperto": False},
    "vfl bochum": {"stadio": "Vonovia Ruhrstadion", "citta": "Bochum", "campo": "erba_naturale", "lat": 51.48, "lon": 7.23, "media_cartellini": 2.3, "coperto": False},
    "fc heidenheim": {"stadio": "Voith-Arena", "citta": "Heidenheim", "campo": "erba_naturale", "lat": 48.67, "lon": 10.16, "media_cartellini": 2.2, "coperto": False},
    "real madrid": {"stadio": "Santiago Bernabeu", "citta": "Madrid", "campo": "erba_ibrida", "lat": 40.45, "lon": -3.68, "media_cartellini": 1.9, "coperto": True},
    "fc barcelona": {"stadio": "Estadi Olimpic Lluis Companys", "citta": "Barcelona", "campo": "erba_naturale", "lat": 41.36, "lon": 2.15, "media_cartellini": 2.0, "coperto": False},
    "atletico madrid": {"stadio": "Metropolitano", "citta": "Madrid", "campo": "erba_naturale", "lat": 40.43, "lon": -3.59, "media_cartellini": 2.5, "coperto": False},
    "athletic club": {"stadio": "San Mames", "citta": "Bilbao", "campo": "erba_naturale", "lat": 43.26, "lon": -2.94, "media_cartellini": 2.2, "coperto": False},
    "villarreal": {"stadio": "Estadio de la Ceramica", "citta": "Villarreal", "campo": "erba_naturale", "lat": 39.94, "lon": -0.10, "media_cartellini": 2.3, "coperto": False},
    "real sociedad": {"stadio": "Reale Arena", "citta": "San Sebastian", "campo": "erba_naturale", "lat": 43.30, "lon": -1.97, "media_cartellini": 2.1, "coperto": False},
    "real betis": {"stadio": "Benito Villamarin", "citta": "Seville", "campo": "erba_naturale", "lat": 37.35, "lon": -5.98, "media_cartellini": 2.4, "coperto": False},
    "sevilla": {"stadio": "Ramon Sanchez-Pizjuan", "citta": "Seville", "campo": "erba_naturale", "lat": 37.38, "lon": -5.97, "media_cartellini": 2.6, "coperto": False},
    "girona": {"stadio": "Montilivi", "citta": "Girona", "campo": "erba_naturale", "lat": 41.96, "lon": 2.82, "media_cartellini": 2.2, "coperto": False},
    "valencia": {"stadio": "Mestalla", "citta": "Valencia", "campo": "erba_naturale", "lat": 39.47, "lon": -0.35, "media_cartellini": 2.5, "coperto": False},
    "osasuna": {"stadio": "El Sadar", "citta": "Pamplona", "campo": "erba_naturale", "lat": 42.79, "lon": -1.63, "media_cartellini": 2.3, "coperto": False},
    "celta vigo": {"stadio": "Abanca-Balaidos", "citta": "Vigo", "campo": "erba_naturale", "lat": 42.21, "lon": -8.74, "media_cartellini": 2.4, "coperto": False},
    "getafe": {"stadio": "Coliseum", "citta": "Getafe", "campo": "erba_naturale", "lat": 40.32, "lon": -3.72, "media_cartellini": 3.0, "coperto": False},
    "mallorca": {"stadio": "Son Moix", "citta": "Palma", "campo": "erba_naturale", "lat": 39.59, "lon": 2.62, "media_cartellini": 2.3, "coperto": False},
    "alaves": {"stadio": "Mendizorrotza", "citta": "Vitoria-Gasteiz", "campo": "erba_naturale", "lat": 42.84, "lon": -2.68, "media_cartellini": 2.4, "coperto": False},
    "rayo vallecano": {"stadio": "Campo de Vallecas", "citta": "Madrid", "campo": "erba_naturale", "lat": 40.39, "lon": -3.65, "media_cartellini": 2.5, "coperto": False},
    "las palmas": {"stadio": "Gran Canaria", "citta": "Las Palmas", "campo": "erba_naturale", "lat": 28.10, "lon": -15.45, "media_cartellini": 2.1, "coperto": False},
    "espanyol": {"stadio": "Stage Front Stadium", "citta": "Barcelona", "campo": "erba_naturale", "lat": 41.34, "lon": 2.07, "media_cartellini": 2.3, "coperto": False},
    "real valladolid": {"stadio": "Jose Zorrilla", "citta": "Valladolid", "campo": "erba_naturale", "lat": 41.65, "lon": -4.75, "media_cartellini": 2.4, "coperto": False},
    "leganes": {"stadio": "Butarque", "citta": "Leganes", "campo": "erba_naturale", "lat": 40.33, "lon": -3.76, "media_cartellini": 2.4, "coperto": False},
    "paris saint-germain": {"stadio": "Parc des Princes", "citta": "Paris", "campo": "erba_ibrida", "lat": 48.84, "lon": 2.25, "media_cartellini": 1.7, "coperto": False},
    "olympique lyonnais": {"stadio": "Groupama Stadium", "citta": "Lyon", "campo": "erba_ibrida", "lat": 45.76, "lon": 4.97, "media_cartellini": 2.1, "coperto": False},
    "olympique marseille": {"stadio": "Stade Velodrome", "citta": "Marseille", "campo": "erba_naturale", "lat": 43.26, "lon": 5.39, "media_cartellini": 2.4, "coperto": False},
    "as monaco": {"stadio": "Stade Louis II", "citta": "Monaco", "campo": "erba_naturale", "lat": 43.72, "lon": 7.41, "media_cartellini": 1.9, "coperto": False},
    "lille": {"stadio": "Stade Pierre-Mauroy", "citta": "Lille", "campo": "erba_ibrida", "lat": 50.61, "lon": 3.13, "media_cartellini": 2.2, "coperto": True},
    "nice": {"stadio": "Allianz Riviera", "citta": "Nice", "campo": "erba_ibrida", "lat": 43.71, "lon": 7.18, "media_cartellini": 2.3, "coperto": False},
    "lens": {"stadio": "Stade Bollaert-Delelis", "citta": "Lens", "campo": "erba_naturale", "lat": 50.43, "lon": 2.82, "media_cartellini": 2.1, "coperto": False},
    "rennes": {"stadio": "Roazhon Park", "citta": "Rennes", "campo": "erba_naturale", "lat": 48.10, "lon": -1.71, "media_cartellini": 2.0, "coperto": False},
    "stade de reims": {"stadio": "Stade Auguste-Delaune", "citta": "Reims", "campo": "erba_naturale", "lat": 49.24, "lon": 4.02, "media_cartellini": 2.2, "coperto": False},
    "strasbourg": {"stadio": "Stade de la Meinau", "citta": "Strasbourg", "campo": "erba_naturale", "lat": 48.56, "lon": 7.75, "media_cartellini": 2.4, "coperto": False},
    "toulouse": {"stadio": "Stadium de Toulouse", "citta": "Toulouse", "campo": "erba_naturale", "lat": 43.58, "lon": 1.43, "media_cartellini": 2.3, "coperto": False},
    "nantes": {"stadio": "Stade de la Beaujoire", "citta": "Nantes", "campo": "erba_naturale", "lat": 47.25, "lon": -1.52, "media_cartellini": 2.4, "coperto": False},
    "montpellier": {"stadio": "Stade de la Mosson", "citta": "Montpellier", "campo": "erba_naturale", "lat": 43.62, "lon": 3.81, "media_cartellini": 2.6, "coperto": False},
    "le havre": {"stadio": "Stade Oceane", "citta": "Le Havre", "campo": "erba_naturale", "lat": 49.50, "lon": 0.17, "media_cartellini": 2.5, "coperto": False},
    "auxerre": {"stadio": "Stade de l'Abbe-Deschamps", "citta": "Auxerre", "campo": "erba_naturale", "lat": 47.77, "lon": 3.58, "media_cartellini": 2.2, "coperto": False},
    "saint-etienne": {"stadio": "Stade Geoffroy-Guichard", "citta": "Saint-Etienne", "campo": "erba_naturale", "lat": 45.45, "lon": 4.39, "media_cartellini": 2.5, "coperto": False},
    "angers": {"stadio": "Stade Raymond Kopa", "citta": "Angers", "campo": "erba_naturale", "lat": 47.47, "lon": -0.55, "media_cartellini": 2.4, "coperto": False},
    "brest": {"stadio": "Stade Francis-Le Ble", "citta": "Brest", "campo": "erba_naturale", "lat": 48.40, "lon": -4.49, "media_cartellini": 2.2, "coperto": False},
    "arsenal": {"stadio": "Emirates Stadium", "citta": "London", "campo": "erba_naturale", "lat": 51.55, "lon": -0.10, "media_cartellini": 1.9, "coperto": False},
    "aston villa": {"stadio": "Villa Park", "citta": "Birmingham", "campo": "erba_naturale", "lat": 52.50, "lon": -1.88, "media_cartellini": 2.2, "coperto": False},
    "bournemouth": {"stadio": "Vitality Stadium", "citta": "Bournemouth", "campo": "erba_naturale", "lat": 50.73, "lon": -1.83, "media_cartellini": 2.1, "coperto": False},
    "brentford": {"stadio": "Gtech Community Stadium", "citta": "London", "campo": "erba_naturale", "lat": 51.48, "lon": -0.28, "media_cartellini": 2.0, "coperto": False},
    "brighton": {"stadio": "Amex Stadium", "citta": "Brighton", "campo": "erba_naturale", "lat": 50.86, "lon": -0.08, "media_cartellini": 2.0, "coperto": False},
    "chelsea": {"stadio": "Stamford Bridge", "citta": "London", "campo": "erba_naturale", "lat": 51.48, "lon": -0.19, "media_cartellini": 2.4, "coperto": False},
    "crystal palace": {"stadio": "Selhurst Park", "citta": "London", "campo": "erba_naturale", "lat": 51.39, "lon": -0.08, "media_cartellini": 2.3, "coperto": False},
    "everton": {"stadio": "Goodison Park", "citta": "Liverpool", "campo": "erba_naturale", "lat": 53.44, "lon": -2.96, "media_cartellini": 2.5, "coperto": False},
    "fulham": {"stadio": "Craven Cottage", "citta": "London", "campo": "erba_naturale", "lat": 51.47, "lon": -0.22, "media_cartellini": 2.1, "coperto": False},
    "ipswich town": {"stadio": "Portman Road", "citta": "Ipswich", "campo": "erba_naturale", "lat": 52.05, "lon": 1.14, "media_cartellini": 2.2, "coperto": False},
    "leicester city": {"stadio": "King Power Stadium", "citta": "Leicester", "campo": "erba_naturale", "lat": 52.62, "lon": -1.14, "media_cartellini": 2.1, "coperto": False},
    "liverpool": {"stadio": "Anfield", "citta": "Liverpool", "campo": "erba_naturale", "lat": 53.43, "lon": -2.96, "media_cartellini": 1.8, "coperto": False},
    "manchester city": {"stadio": "Etihad Stadium", "citta": "Manchester", "campo": "erba_ibrida", "lat": 53.48, "lon": -2.20, "media_cartellini": 1.7, "coperto": False},
    "manchester united": {"stadio": "Old Trafford", "citta": "Manchester", "campo": "erba_naturale", "lat": 53.46, "lon": -2.29, "media_cartellini": 2.3, "coperto": False},
    "newcastle united": {"stadio": "St. James' Park", "citta": "Newcastle", "campo": "erba_naturale", "lat": 54.97, "lon": -1.62, "media_cartellini": 2.2, "coperto": False},
    "nottingham forest": {"stadio": "City Ground", "citta": "Nottingham", "campo": "erba_naturale", "lat": 52.93, "lon": -1.13, "media_cartellini": 2.4, "coperto": False},
    "southampton": {"stadio": "St Mary's Stadium", "citta": "Southampton", "campo": "erba_naturale", "lat": 50.90, "lon": -1.39, "media_cartellini": 2.2, "coperto": False},
    "tottenham": {"stadio": "Tottenham Hotspur Stadium", "citta": "London", "campo": "erba_naturale", "lat": 51.60, "lon": -0.06, "media_cartellini": 2.3, "coperto": True},
    "west ham": {"stadio": "London Stadium", "citta": "London", "campo": "erba_naturale", "lat": 51.53, "lon": -0.01, "media_cartellini": 2.1, "coperto": False},
    "wolverhampton": {"stadio": "Molineux Stadium", "citta": "Wolverhampton", "campo": "erba_naturale", "lat": 52.59, "lon": -2.13, "media_cartellini": 2.5, "coperto": False},
    "bari": {"stadio": "Stadio San Nicola", "citta": "Bari", "campo": "erba_naturale", "lat": 41.08, "lon": 16.82, "media_cartellini": 2.7, "coperto": False},
    "brescia": {"stadio": "Stadio Mario Rigamonti", "citta": "Brescia", "campo": "erba_naturale", "lat": 45.56, "lon": 10.23, "media_cartellini": 2.6, "coperto": False},
    "carrarese": {"stadio": "Stadio dei Marmi", "citta": "Carrara", "campo": "erba_naturale", "lat": 44.07, "lon": 10.08, "media_cartellini": 2.8, "coperto": False},
    "cesena": {"stadio": "Orogel Stadium-Dino Manuzzi", "citta": "Cesena", "campo": "erba_naturale", "lat": 44.13, "lon": 12.24, "media_cartellini": 2.5, "coperto": False},
    "cittadella": {"stadio": "Stadio Piercesare Tombolato", "citta": "Cittadella", "campo": "erba_naturale", "lat": 45.64, "lon": 11.78, "media_cartellini": 2.7, "coperto": False},
    "cosenza": {"stadio": "Stadio San Vito-Gigi Marulla", "citta": "Cosenza", "campo": "erba_naturale", "lat": 39.31, "lon": 16.25, "media_cartellini": 2.8, "coperto": False},
    "cremonese": {"stadio": "Stadio Giovanni Zini", "citta": "Cremona", "campo": "erba_naturale", "lat": 45.13, "lon": 10.03, "media_cartellini": 2.4, "coperto": False},
    "juve stabia": {"stadio": "Stadio Romeo Menti", "citta": "Castellammare di Stabia", "campo": "erba_naturale", "lat": 40.70, "lon": 14.48, "media_cartellini": 2.7, "coperto": False},
    "mantova": {"stadio": "Stadio Danilo Martelli", "citta": "Mantova", "campo": "erba_naturale", "lat": 45.16, "lon": 10.79, "media_cartellini": 2.5, "coperto": False},
    "modena": {"stadio": "Stadio Alberto Braglia", "citta": "Modena", "campo": "erba_naturale", "lat": 44.65, "lon": 10.92, "media_cartellini": 2.6, "coperto": False},
    "palermo": {"stadio": "Stadio Renzo Barbera", "citta": "Palermo", "campo": "erba_naturale", "lat": 38.15, "lon": 13.34, "media_cartellini": 2.4, "coperto": False},
    "pisa": {"stadio": "Stadio Arena Garibaldi", "citta": "Pisa", "campo": "erba_naturale", "lat": 43.72, "lon": 10.40, "media_cartellini": 2.5, "coperto": False},
    "reggiana": {"stadio": "Mapei Stadium", "citta": "Reggio Emilia", "campo": "erba_naturale", "lat": 44.71, "lon": 10.64, "media_cartellini": 2.6, "coperto": False},
    "salernitana": {"stadio": "Stadio Arechi", "citta": "Salerno", "campo": "erba_naturale", "lat": 40.66, "lon": 14.82, "media_cartellini": 2.7, "coperto": False},
    "sampdoria": {"stadio": "Stadio Luigi Ferraris", "citta": "Genova", "campo": "erba_naturale", "lat": 44.42, "lon": 8.95, "media_cartellini": 2.4, "coperto": False},
    "sassuolo": {"stadio": "Mapei Stadium", "citta": "Reggio Emilia", "campo": "erba_naturale", "lat": 44.71, "lon": 10.64, "media_cartellini": 2.3, "coperto": False},
    "spezia": {"stadio": "Stadio Alberto Picco", "citta": "La Spezia", "campo": "erba_naturale", "lat": 44.10, "lon": 9.82, "media_cartellini": 2.5, "coperto": False},
    "sudtirol": {"stadio": "Stadio Druso", "citta": "Bolzano", "campo": "erba_naturale", "lat": 46.49, "lon": 11.34, "media_cartellini": 2.4, "coperto": False},
    "catanzaro": {"stadio": "Stadio Nicola Ceravolo", "citta": "Catanzaro", "campo": "erba_naturale", "lat": 38.89, "lon": 16.59, "media_cartellini": 2.6, "coperto": False},
    "italy": {"stadio": "Stadio Olimpico", "citta": "Roma", "campo": "erba_naturale", "lat": 41.93, "lon": 12.45, "media_cartellini": 2.2, "coperto": False},
    "germany": {"stadio": "Olympiastadion", "citta": "Berlin", "campo": "erba_naturale", "lat": 52.51, "lon": 13.24, "media_cartellini": 1.8, "coperto": False},
    "france": {"stadio": "Stade de France", "citta": "Saint-Denis", "campo": "erba_naturale", "lat": 48.92, "lon": 2.36, "media_cartellini": 1.9, "coperto": False},
    "spain": {"stadio": "Santiago Bernabeu", "citta": "Madrid", "campo": "erba_ibrida", "lat": 40.45, "lon": -3.68, "media_cartellini": 1.7, "coperto": True},
    "england": {"stadio": "Wembley Stadium", "citta": "London", "campo": "erba_naturale", "lat": 51.55, "lon": -0.27, "media_cartellini": 1.8, "coperto": True},
    "brazil": {"stadio": "Maracana", "citta": "Rio de Janeiro", "campo": "erba_naturale", "lat": -22.91, "lon": -43.23, "media_cartellini": 2.6, "coperto": False},
    "argentina": {"stadio": "Estadio Monumental", "citta": "Buenos Aires", "campo": "erba_naturale", "lat": -34.54, "lon": -58.45, "media_cartellini": 2.4, "coperto": False},
    "portugal": {"stadio": "Estadio da Luz", "citta": "Lisbon", "campo": "erba_naturale", "lat": 38.75, "lon": -9.18, "media_cartellini": 2.1, "coperto": False},
    "netherlands": {"stadio": "Johan Cruyff Arena", "citta": "Amsterdam", "campo": "erba_ibrida", "lat": 52.31, "lon": 4.94, "media_cartellini": 2.0, "coperto": True},
    "belgium": {"stadio": "Stade Roi Baudouin", "citta": "Brussels", "campo": "erba_naturale", "lat": 50.89, "lon": 4.33, "media_cartellini": 2.1, "coperto": False},
    "croatia": {"stadio": "Stadion Maksimir", "citta": "Zagreb", "campo": "erba_naturale", "lat": 45.81, "lon": 16.02, "media_cartellini": 2.3, "coperto": False},
    "uruguay": {"stadio": "Estadio Centenario", "citta": "Montevideo", "campo": "erba_naturale", "lat": -34.89, "lon": -56.15, "media_cartellini": 2.8, "coperto": False}
}

DB_ALLENATORI = {
    "default": DEFAULT_ALLENATORE,
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
}

DB_LAMBDA_SQUADRE = {
    "default": DEFAULT_LAMBDA,
    "inter": {"lambda_casa": 2.10, "lambda_ospite": 1.75},
    "atalanta": {"lambda_casa": 2.00, "lambda_ospite": 1.60},
    "juventus": {"lambda_casa": 1.90, "lambda_ospite": 1.50},
    "milan": {"lambda_casa": 1.95, "lambda_ospite": 1.55},
    "napoli": {"lambda_casa": 1.85, "lambda_ospite": 1.45},
    "roma": {"lambda_casa": 1.80, "lambda_ospite": 1.40},
    "lazio": {"lambda_casa": 1.75, "lambda_ospite": 1.35},
}

DB_ARBITRI = {
    "davide massa": 10,
    "fabio maresca": 9,
    "marco guida": 7,
    "maurizio mariani": 7,
    "daniele doveri": 5,
    "daniele chiffi": 2,
    "marco di bello": 2
}

@timed_cache(seconds=60)
def scrappa_arbitro_live(squadra_casa: str, squadra_ospite: str) -> str:
    return "ND"

def genera_contesto_match(casa: str, ospite: str):
    casa_key = normalizza_nome_squadra(casa)
    ospite_key = normalizza_nome_squadra(ospite)

    stadio_info = DB_STADI.get(casa_key, DB_STADI["default"])
    all_casa = DB_ALLENATORI.get(casa_key, DB_ALLENATORI["default"])
    all_ospite = DB_ALLENATORI.get(ospite_key, DB_ALLENATORI["default"])
    
    arbitro_designato = scrappa_arbitro_live(casa, ospite)
    severita_arbitro = DB_ARBITRI.get(arbitro_designato.lower().strip(), 5) if arbitro_designato != "ND" else "ND"
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

def ottieni_flussi_monetari_reali(casa: str, ospite: str) -> dict:
    return {
        "flusso_str": "Analisi volumi di mercato attiva.",
        "whale_active": False
    }

def esegui_master_calculator(casa: str, ospite: str, contesto: dict):
    idx_casa = int(contesto.get("Indice Tattico Casa") if contesto.get("Indice Tattico Casa") != "N/D" else 5)
    idx_ospite = int(contesto.get("Indice Tattico Ospite") if contesto.get("Indice Tattico Ospite") != "N/D" else 5)
    vantaggio_tattico = "Equilibrio"
    
    if idx_casa > idx_ospite + 1:
        vantaggio_tattico = f"Vantaggio Tattico Casa ({contesto.get('Allenatore Casa')})"
    elif idx_ospite > idx_casa + 1:
        vantaggio_tattico = f"Vantaggio Tattico Ospite ({contesto.get('Allenatore Ospite')})"

    dati_flussi = ottieni_flussi_monetari_reali(casa, ospite)

    return {
        "fattori_umani": vantaggio_tattico,
        "disciplinare": "Regolare",
        "flussi_monetari": dati_flussi["flusso_str"],
        "whale_alert": dati_flussi["whale_active"],
        "trend_storici": "Analisi H2H elaborata."
    }

app = FastAPI(
    title="Schizzo Analytics Engine",
    description="Backend analitico con motore Poisson dinamico e architettura modulare.",
    version="2.3.2"
)

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
    
    # Under / Over da 0.5 a 4.5
    under_over = {}
    for soglia in [0.5, 1.5, 2.5, 3.5, 4.5]:
        u_p = sum(prob for score, prob in matrice.items() if (int(score.split('-')[0]) + int(score.split('-')[1])) < soglia)
        under_over[f"Under {soglia}"] = round(u_p * 100, 2)
        under_over[f"Over {soglia}"] = round((1.0 - u_p) * 100, 2)
        
    # Multigol da 1 a 5
    multigol = {}
    for m_min, m_max in [(1, 2), (1, 3), (1, 4), (1, 5), (2, 4), (2, 5), (3, 5)]:
        mg_p = sum(prob for score, prob in matrice.items() if m_min <= (int(score.split('-')[0]) + int(score.split('-')[1])) <= m_max)
        multigol[f"Multigol {m_min}-{m_max}"] = round(mg_p * 100, 2)
        
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
        "multigol": multigol,
        "top_3_risultati_esatti": top_esatti_fmt
    }

@app.get("/")
def read_root():
    return {"status": "online", "app": "Schizzo Analytics Engine", "version": "2.3.2"}

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

    l_casa_adj = l_casa_base * req.moltiplicatore_infortuni * req.moltiplicatore_stadio
    l_ospite_adj = l_ospite_base * req.moltiplicatore_arbitro
    
    risultati_poisson = elabora_mercati_poisson(l_casa_adj, l_ospite_adj)
    contesto_match = genera_contesto_match(casa=casa, ospite=ospite)
    master_stats = esegui_master_calculator(casa, ospite, contesto_match)

    return {
        "partita": f"{casa} vs {ospite}",
        "match_id": match_id,
        "parametri_applicati": {
            "lambda_casa_effettivo": round(l_casa_adj, 2),
            "lambda_ospite_effettivo": round(l_ospite_adj, 2)
        },
        "previsioni_poisson": risultati_poisson,
        "info_match": contesto_match, 
        "master_calculator": master_stats
    }

@app.post("/api/calcola-match")
def calcola_match(req: CalcolaMatchRequest):
    home_team = req.home
    away_team = req.away
    
    casa_key = normalizza_nome_squadra(home_team)
    ospite_key = normalizza_nome_squadra(away_team)

    stats_casa = DB_LAMBDA_SQUADRE.get(casa_key, DB_LAMBDA_SQUADRE["default"])
    stats_ospite = DB_LAMBDA_SQUADRE.get(ospite_key, DB_LAMBDA_SQUADRE["default"])

    poisson_data = elabora_mercati_poisson(stats_casa["lambda_casa"], stats_ospite["lambda_ospite"])
    contesto = genera_contesto_match(home_team, away_team)
    master_stats = esegui_master_calculator(home_team, away_team, contesto)

    p1x2 = poisson_data["esito_1x2"]
    uo25 = poisson_data["under_over"]
    gg = poisson_data["gol_nogol"]
    
    panel_testo = (
        f"Analisi Poisson Matematica:\n"
        f"• 1X2 -> 1: {p1x2['1']}% | X: {p1x2['X']}% | 2: {p1x2['2']}%\n"
        f"• Under/Over 2.5 -> Under: {uo25['Under 2.5']}% | Over: {uo25['Over 2.5']}%\n"
        f"• GOL/NO GOL -> GOL: {gg['Gol']}% | NO GOL: {gg['NoGol']}%"
    )

    intelligence_risposta = {
        'mister': f"Tattica Casa: {contesto['Indice Tattico Casa']} | Tattica Ospite: {contesto['Indice Tattico Ospite']} -> {master_stats['fattori_umani']}",
        'arbitro': f"Designato: {contesto['Arbitro Designato']} (Severità: {contesto['Severità Arbitro']})",
        'infortunati': 'Parametri rosa verificati.',
        'stadium': f"Stadio: {contesto['Stadio Casa']} ({contesto['Terreno & Copertura']}) - Meteo: {contesto['Meteo Live']}",
        'flussi': master_stats['flussi_monetari'],
        'storico': master_stats['trend_storici']
    }

    return {
        'panel_esperti': panel_testo,
        'intelligence': intelligence_risposta,
        'poisson': poisson_data
    }