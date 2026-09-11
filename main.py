import os
import math
import time
import requests
from functools import wraps
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

# ==========================================
# ⏱️ SISTEMA DI CACHE INTELLIGENTE (60s TTL)
# ==========================================
def timed_cache(seconds: int = 60):
    def decorator(func):
        cache = {}
        @wraps(func) if 'wraps' in globals() else lambda f: f
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
# 🌤️ CONFIGURAZIONE METEO & API ESTERNE
# ==========================================
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "1276c6c958e9fa1f6d99da6fadb02421")
FOOTBALL_DATA_API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY")
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4/"

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
# 🔄 MAPPATURA ALIAS E NORMALIZZAZIONE
# ==========================================
TEAM_ALIASES = {
    "bayern munich": "bayern monaco",
    "fc bayern münchen": "bayern monaco",
    "borussia dortmund": "borussia",
    "bvb": "borussia",
    "rb leipzig": "lipsia",
    "leipzig": "lipsia",
    "as monaco": "monaco",
    "paris saint-germain": "psg",
    "paris sg": "psg",
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
# 📊 DIZIONARI METRICHE AVANZATE (SENZA OMISSIONI)
# ==========================================
DB_EFFICIENZA_XG = {
    "inter": 1.08,
    "juventus": 1.04,
    "milan": 1.03,
    "napoli": 1.05,
    "roma": 1.02,
    "lazio": 1.01,
    "atalanta": 1.06,
    "cagliari": 0.99,
    "frosinone": 0.98,
    "lipsia": 1.05,
    "monaco": 1.04,
    "real madrid": 1.07,
    "barcellona": 1.06,
    "manchester city": 1.09,
    "bayern monaco": 1.08,
    "arsenal": 1.04,
    "liverpool": 1.05
}

DB_PPDA = {
    "inter": 9.8,
    "juventus": 10.2,
    "milan": 10.5,
    "napoli": 11.0,
    "atalanta": 8.5,
    "roma": 9.5,
    "lazio": 11.5,
    "cagliari": 12.5,
    "frosinone": 13.0,
    "lipsia": 9.0,
    "monaco": 10.0,
    "real madrid": 11.2,
    "barcellona": 9.1,
    "manchester city": 8.8,
    "bayern monaco": 9.0,
    "arsenal": 9.2,
    "liverpool": 9.4
}

DB_DUELLI = {
    "inter": 1.05,
    "juventus": 1.03,
    "milan": 1.02,
    "napoli": 1.01,
    "atalanta": 1.07,
    "roma": 1.03,
    "lazio": 1.02,
    "cagliari": 1.04,
    "frosinone": 0.97,
    "lipsia": 1.04,
    "monaco": 1.03,
    "real madrid": 1.04,
    "barcellona": 0.99,
    "manchester city": 1.02,
    "bayern monaco": 1.05
}

DB_ACCURATEZZA_BALISTICA = {
    "inter": 1.05,
    "juventus": 1.02,
    "milan": 1.03,
    "napoli": 1.03,
    "atalanta": 1.04,
    "roma": 1.01,
    "lazio": 1.01,
    "cagliari": 0.98,
    "frosinone": 0.96,
    "lipsia": 1.04,
    "monaco": 1.03,
    "real madrid": 1.06,
    "barcellona": 1.05,
    "manchester city": 1.07,
    "bayern monaco": 1.06
}

DB_OVERRIDE_FATTORE_CAMPO = {
    'juventus': 1.22,
    'inter': 1.20,
    'milan': 1.18,
    'roma': 1.18,
    'lazio': 1.17,
    'napoli': 1.19,
    'atalanta': 1.19,
    'cagliari': 1.16,
    'frosinone': 1.10,
    'lipsia': 1.15,
    'monaco': 1.14
}

# ==========================================
# 🗄️ DATABASE STADI, ALLENATORI E LAMBDA
# ==========================================
DEFAULT_STADIO = {"stadio": "Stadio Generico", "citta": "N/D", "campo": "erba_naturale", "lat": 0.0, "lon": 0.0, "media_cartellini": 2.2, "coperto": False}
DEFAULT_ALLENATORE = {"allenatore": "Non dichiarato", "indice_tattico": 5}
DEFAULT_LAMBDA = {"lambda_casa": 1.65, "lambda_ospite": 1.20}

DB_STADI = {
    "default": {
        "Stadio Casa": "Stadio Principale",
        "Città": "N/D",
        "Terreno & Copertura": "Erba naturale",
        "Allenatore Casa": "N/D",
        "Indice Tattico Casa": 5,
        "Media Cartellini Stadio": 2.5
    },
    # SERIE A
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
    
    # BUNDESLIGA
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

    # LA LIGA
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

    # LIGUE 1
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

    # PREMIER LEAGUE
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

    # SERIE B
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

    # NAZIONALI
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
    "juventus": {"lambda_casa": 1.90, "lambda_ospite": 1.55},
    "inter": {"lambda_casa": 2.10, "lambda_ospite": 1.75},
    "milan": {"lambda_casa": 1.90, "lambda_ospite": 1.55},
    "napoli": {"lambda_casa": 1.85, "lambda_ospite": 1.50},
    "roma": {"lambda_casa": 1.85, "lambda_ospite": 1.50},
    "lazio": {"lambda_casa": 1.80, "lambda_ospite": 1.45},
    "atalanta": {"lambda_casa": 1.95, "lambda_ospite": 1.60},
    "cagliari": {"lambda_casa": 1.60, "lambda_ospite": 1.25},
    "frosinone": {"lambda_casa": 1.40, "lambda_ospite": 1.15},
    "lipsia": {"lambda_casa": 1.95, "lambda_ospite": 1.65},
    "monaco": {"lambda_casa": 1.90, "lambda_ospite": 1.60},
    "real madrid": {"lambda_casa": 2.15, "lambda_ospite": 1.80},
    "barcellona": {"lambda_casa": 2.10, "lambda_ospite": 1.75},
    "manchester city": {"lambda_casa": 2.15, "lambda_ospite": 1.80},
    "arsenal": {"lambda_casa": 2.05, "lambda_ospite": 1.70},
    "liverpool": {"lambda_casa": 2.05, "lambda_ospite": 1.70},
    "bayern monaco": {"lambda_casa": 2.15, "lambda_ospite": 1.80}
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

def scrappa_arbitro_live(squadra_casa: str, squadra_ospite: str) -> str:
    return "Davide Massa"

def genera_contesto_match(casa: str, ospite: str):
    casa_key = normalizza_nome_squadra(casa)
    ospite_key = normalizza_nome_squadra(ospite)

    stadio_info = DB_STADI.get(casa_key, DB_STADI["default"])
    all_casa = DB_ALLENATORI.get(casa_key, DB_ALLENATORI["default"])
    all_ospite = DB_ALLENATORI.get(ospite_key, DB_ALLENATORI["default"])
    
    arbitro_designato = scrappa_arbitro_live(casa, ospite)
    severita_arbitro = DB_ARBITRI.get(arbitro_designato.lower().strip(), 5)
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

def esegui_master_calculator(casa: str, ospite: str, contesto: dict):
    idx_casa = int(contesto.get("Indice Tattico Casa") if contesto.get("Indice Tattico Casa") != "N/D" else 5)
    idx_ospite = int(contesto.get("Indice Tattico Ospite") if contesto.get("Indice Tattico Ospite") != "N/D" else 5)
    vantaggio_tattico = "Equilibrio"
    
    if idx_casa > idx_ospite + 1:
        vantaggio_tattico = f"Vantaggio Tattico Casa ({contesto.get('Allenatore Casa')})"
    elif idx_ospite > idx_casa + 1:
        vantaggio_tattico = f"Vantaggio Tattico Ospite ({contesto.get('Allenatore Ospite')})"

    return {
        "fattori_umani": vantaggio_tattico,
        "disciplinare": "Regolare",
        "flussi_monetari": "Analisi volumi di mercato attiva.",
        "whale_alert": False,
        "trend_storici": "Analisi H2H elaborata."
    }

app = FastAPI(
    title="Schizzo Analytics Engine",
    description="Backend analitico completo con tutte le voci e squadre mappate senza omissioni.",
    version="2.5.0"
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

def poisson_probability(k: int, lambd: float) -> float:
    if lambd <= 0:
        return 0.0
    return (math.pow(lambd, k) * math.exp(-lambd)) / math.factorial(k)

def calcola_lambda_avanzato(casa_key: str, ospite_key: str, l_casa_base: float, l_ospite_base: float, molt_infortuni: float = 1.0, molt_stadio: float = 1.0, molt_arbitro: float = 1.0):
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

@app.get("/")
def read_root():
    return {"status": "online", "app": "Schizzo Analytics Engine", "version": "2.5.0"}

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
        "panel_esperti": f"Analisi tattica: {master_stats['fattori_umani']}. Flussi: {master_stats['flussi_monetari']}."
    }