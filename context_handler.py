import os
import requests

def genera_contesto_match(squadra_casa: str, squadra_ospite: str, db_stadi: dict, db_allenatori: dict, db_arbitri: dict) -> dict:
    """
    Genera il dizionario di contesto per la UI Flutter combinando:
    - Stadio, terreno e copertura dal database stadi (con lat/lon)
    - Meteo live tramite OpenWeatherMap basato sulle coordinate dello stadio
    - Allenatori aggiornati (calciomercato) e indice di bravura
    - Arbitro designato e indice di severità
    """
    
    # 1. Recupero dati stadio e coordinate (Lat/Lon)
    info_stadio = db_stadi.get(squadra_casa, {
        "nome": "Stadio Principale",
        "terreno": "Erba Naturale",
        "copertura": "Scoperto",
        "lat": 41.9028,
        "lon": 12.4964
    })
    
    # 2. Chiamata OpenWeatherMap in tempo reale
    api_key_weather = os.getenv("OPENWEATHER_API_KEY", "")
    lat, lon = info_stadio.get("lat"), info_stadio.get("lon")
    
    meteo_str = "Meteo non disponibile"
    if api_key_weather:
        try:
            url_weather = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key_weather}&units=metric&lang=it"
            res = requests.get(url_weather, timeout=3)
            if res.status_code == 200:
                w_data = res.json()
                temp = w_data['main']['temp']
                desc = w_data['weather'][0]['description']
                meteo_str = f"{temp}°C, {desc.capitalize()}"
        except Exception:
            meteo_str = "Errore connessione meteo"
    else:
        meteo_str = "API Key Meteo mancante"

    # 3. Recupero allenatori aggiornati (Calciomercato)
    mister_casa = db_allenatori.get(squadra_casa, {"nome": "Da aggiornare", "indice": "N/D"})
    mister_ospite = db_allenatori.get(squadra_ospite, {"nome": "Da aggiornare", "indice": "N/D"})

    # 4. Recupero arbitro designato e indice di severità
    match_key = f"{squadra_casa}_{squadra_ospite}"
    arbitro_info = db_arbitri.get(match_key, db_arbitri.get("default", {"nome": "Designazione in corso", "severita": "N/D"}))

    # 5. Restituzione del dizionario mappato per la UI Flutter
    return {
        "STADIO": info_stadio.get("nome", "Stadio Ufficiale"),
        "TERRENO": info_stadio.get("terreno", "Erba Naturale"),
        "COPERTURA": info_stadio.get("copertura", "Scoperto"),
        "METEO LIVE": meteo_str,
        "ALLENATORE CASA": f"{mister_casa['nome']} (Indice: {mister_casa['indice']})",
        "ALLENATORE OSPITE": f"{mister_ospite['nome']} (Indice: {mister_ospite['indice']})",
        "ARBITRO & SEVERITÀ": f"{arbitro_info['nome']} (Severità: {arbitro_info['severita']})"
    }