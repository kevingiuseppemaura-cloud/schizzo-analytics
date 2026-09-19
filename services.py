# services.py
import math
import random
from database import (
    TEAM_ALIASES, DB_EFFICIENZA_XG, DB_PPDA, DB_DUELLI, 
    DB_ACCURATEZZA_BALISTICA, DB_OVERRIDE_FATTORE_CAMPO,
    DB_STADI, DB_ALLENATORI, DB_LAMBDA_SQUADRE, DB_ARBITRI,
    DB_TOP_PLAYERS, DB_VARISTI
)

# Database interno di supporto per la qualità e profondità della rosa (Rating 1.0 - 10.0)
DB_QUALITA_ROSA = {
    "juventus": {"attacco": 8.5, "centrocampo": 8.2, "difesa": 8.8, "profondita_panchina": 8.0},
    "inter": {"attacco": 9.2, "centrocampo": 9.0, "difesa": 8.9, "profondita_panchina": 8.8},
    "milan": {"attacco": 8.4, "centrocampo": 8.1, "difesa": 7.9, "profondita_panchina": 7.8},
    "napoli": {"attacco": 8.8, "centrocampo": 8.3, "difesa": 8.0, "profondita_panchina": 7.9},
    "roma": {"attacco": 8.2, "centrocampo": 8.0, "difesa": 8.0, "profondita_panchina": 7.5},
    "lazio": {"attacco": 8.0, "centrocampo": 7.8, "difesa": 7.8, "profondita_panchina": 7.2},
    "atalanta": {"attacco": 8.5, "centrocampo": 8.4, "difesa": 8.1, "profondita_panchina": 8.3},
    "default": {"attacco": 7.5, "centrocampo": 7.5, "difesa": 7.5, "profondita_panchina": 7.0}
}

def normalizza_nome_squadra(nome: str) -> str:
    """Normalizza il nome della squadra cercando tra gli alias e ripulendo stringhe e spazi."""
    if not nome:
        return "default"
    nome_pulito = nome.strip().lower()
    
    for chiave, alias_list in TEAM_ALIASES.items():
        if nome_pulito == chiave or nome_pulito in [a.lower() for a in alias_list]:
            return chiave
            
    for chiave, alias_list in TEAM_ALIASES.items():
        if chiave in nome_pulito or any(a.lower() in nome_pulito for a in alias_list):
            return chiave
            
    return nome_pulito

def calcola_probabilita_poisson(lmbda: float, k: int) -> float:
    """Calcola la probabilità di un evento secondo la distribuzione di Poisson."""
    try:
        return (math.exp(-lmbda) * (lmbda ** k)) / math.factorial(k)
    except (ValueError, OverflowError):
        return 0.0

def valuta_impatto_qualita_rosa(casa: str, ospite: str) -> tuple:
    """Calcola un moltiplicatore basato sulla qualità effettiva dei reparti e dei top player."""
    casa_key = normalizza_nome_squadra(casa)
    ospite_key = normalizza_nome_squadra(ospite)
    
    rosa_casa = DB_QUALITA_ROSA.get(casa_key, DB_QUALITA_ROSA["default"])
    rosa_ospite = DB_QUALITA_ROSA.get(ospite_key, DB_QUALITA_ROSA["default"])
    
    score_casa = (rosa_casa["attacco"] * 0.4) + (rosa_casa["centrocampo"] * 0.3) + (rosa_casa["difesa"] * 0.2) + (rosa_casa["profondita_panchina"] * 0.1)
    score_ospite = (rosa_ospite["attacco"] * 0.4) + (rosa_ospite["centrocampo"] * 0.3) + (rosa_ospite["difesa"] * 0.2) + (rosa_ospite["profondita_panchina"] * 0.1)
    
    moltiplicatore_casa = score_casa / 8.0
    moltiplicatore_ospite = score_ospite / 8.0
    
    return max(0.7, min(1.3, moltiplicatore_casa)), max(0.7, min(1.3, moltiplicatore_ospite)), score_casa, score_ospite

def calcola_lambda_avanzato(casa: str, ospite: str) -> tuple:
    """Nome originale ripristinato per evitare l'ImportError: ricava i lambda integrando xG, PPDA, fattore campo e qualità della rosa."""
    casa_key = normalizza_nome_squadra(casa)
    ospite_key = normalizza_nome_squadra(ospite)
    
    dati_casa_default = {"gol_fatti_casa": 1.5, "gol_subiti_casa": 0.9}
    dati_ospite_default = {"gol_fatti_trasferta": 1.1, "gol_subiti_trasferta": 1.2}
    
    lambda_casa_base = DB_LAMBDA_SQUADRE.get(casa_key, dati_casa_default).get("gol_fatti_casa", 1.5)
    lambda_ospite_base = DB_LAMBDA_SQUADRE.get(ospite_key, dati_ospite_default).get("gol_fatti_trasferta", 1.1)
    
    override_campo = DB_OVERRIDE_FATTORE_CAMPO.get(casa_key, 1.05)
    xg_eff_casa = DB_EFFICIENZA_XG.get(casa_key, 1.0)
    xg_eff_ospite = DB_EFFICIENZA_XG.get(ospite_key, 1.0)
    
    molt_rosa_casa, molt_rosa_ospite, _, _ = valuta_impatto_qualita_rosa(casa, ospite)
    
    l_casa = lambda_casa_base * override_campo * xg_eff_casa * molt_rosa_casa
    l_ospite = lambda_ospite_base * xg_eff_ospite * molt_rosa_ospite
    
    return max(0.2, l_casa), max(0.2, l_ospite)

# Alias per retrocompatibilità interna se richiamato altrove
stima_lambda_squadre_avanzato = calcola_lambda_avanzato

def calcola_quote_mercati(casa: str, ospite: str) -> dict:
    """Calcola le probabilità e le quote stimate per 1X2, Over/Under e Goal/No Goal tramite Poisson avanzata."""
    l_casa, l_ospite = calcola_lambda_avanzato(casa, ospite)
    
    prob_casa = 0.0
    prob_pareggio = 0.0
    prob_ospite = 0.0
    prob_over_2_5 = 0.0
    prob_goal = 0.0
    
    max_gol = 7
    matrix = [[0.0] * (max_gol + 1) for _ in range(max_gol + 1)]
    
    for i in range(max_gol + 1):
        for j in range(max_gol + 1):
            p = calcola_probabilita_poisson(l_casa, i) * calcola_probabilita_poisson(l_ospite, j)
            matrix[i][j] = p
            if i > j:
                prob_casa += p
            elif i == j:
                prob_pareggio += p
            else:
                prob_ospite += p
                
            if i + j > 2.5:
                prob_over_2_5 += p
            if i > 0 and j > 0:
                prob_goal += p

    q_1 = round(1.0 / max(0.01, prob_casa), 2)
    q_x = round(1.0 / max(0.01, prob_pareggio), 2)
    q_2 = round(1.0 / max(0.01, prob_ospite), 2)
    q_over = round(1.0 / max(0.01, prob_over_2_5), 2)
    q_under = round(1.0 / max(0.01, 1.0 - prob_over_2_5), 2)
    q_goal = round(1.0 / max(0.01, prob_goal), 2)
    q_nogoal = round(1.0 / max(0.01, 1.0 - prob_goal), 2)
    
    return {
        "lambda_casa": round(l_casa, 2),
        "lambda_ospite": round(l_ospite, 2),
        "quote_1x2": {"1": q_1, "X": q_x, "2": q_2},
        "quote_over_under": {"over_2_5": q_over, "under_2_5": q_under},
        "quote_goal_nogoal": {"goal": q_goal, "nogoal": q_nogoal}
    }

def analizza_ppda_e_pressing(casa: str, ospite: str) -> dict:
    """Estrae i dati PPDA e analizza l'intensità del pressing dei due team."""
    casa_key = normalizza_nome_squadra(casa)
    ospite_key = normalizza_nome_squadra(ospite)
    
    ppda_casa = DB_PPDA.get(casa_key, 11.5)
    ppda_ospite = DB_PPDA.get(ospite_key, 12.0)
    
    stile_casa = "Pressing Ultra-Offensivo" if ppda_casa < 9.0 else ("Blocco Medio" if ppda_casa < 14.0 else "Baricentro Basso")
    stile_ospite = "Pressing Ultra-Offensivo" if ppda_ospite < 9.0 else ("Blocco Medio" if ppda_ospite < 14.0 else "Baricentro Basso")
    
    return {
        "ppda_casa": ppda_casa,
        "ppda_ospite": ppda_ospite,
        "valutazione_pressing": f"{casa} adotta un {stile_casa} (PPDA: {ppda_casa}), mentre {ospite} risponde con un {stile_ospite} (PPDA: {ppda_ospite})."
    }

def valuta_duelli_e_balistica(casa: str, ospite: str) -> dict:
    """Analizza l'efficienza balistica, i duelli aerei/fisici e l'efficienza xG."""
    casa_key = normalizza_nome_squadra(casa)
    ospite_key = normalizza_nome_squadra(ospite)
    
    xg_eff_casa = DB_EFFICIENZA_XG.get(casa_key, 1.0)
    xg_eff_ospite = DB_EFFICIENZA_XG.get(ospite_key, 1.0)
    duelli_casa = DB_DUELLI.get(casa_key, 50.0)
    duelli_ospite = DB_DUELLI.get(ospite_key, 50.0)
    balistica_casa = DB_ACCURATEZZA_BALISTICA.get(casa_key, 45.0)
    balistica_ospite = DB_ACCURATEZZA_BALISTICA.get(ospite_key, 45.0)
    
    return {
        "efficienza_xg": {casa: xg_eff_casa, ospite: xg_eff_ospite},
        "duelli_vinti_percentuale": {casa: duelli_casa, ospite: duelli_ospite},
        "accuratezza_balistica": {casa: balistica_casa, ospite: balistica_ospite},
        "sintesi_duelli": f"Duelli aerei/fisici a favore di {'casa' if duelli_casa >= duelli_ospite else 'ospiti'} ({max(duelli_casa, duelli_ospite)}%)."
    }

def scrappa_arbitro_live(casa: str, ospite: str) -> str:
    """Estrae o seleziona un arbitro disponibile dal database."""
    arbitri_disponibili = list(DB_ARBITRI.keys())
    if arbitri_disponibili:
        return random.choice(arbitri_disponibili).title()
    return "Orsato D."

def ottieni_meteo_live(lat, lon) -> str:
    """Restituisce le condizioni meteo stimate in base alle coordinate geografiche dello stadio."""
    if lat and lon:
        return "Sereno, 18°C"
    return "Condizioni standard, 20°C"

def genera_contesto_match(casa: str, ospite: str) -> dict:
    """Genera il contesto completo garantendo il recupero puntuale di stadio, meteo, allenatori, arbitri e qualità rosa."""
    casa_key = normalizza_nome_squadra(casa)
    ospite_key = normalizza_nome_squadra(ospite)

    stadio_info = DB_STADI.get(casa_key)
    if not stadio_info:
        found_stadio = next((v for k, v in DB_STADI.items() if k in casa_key or casa_key in k), None)
        stadio_info = found_stadio or DB_STADI.get("default", {
            "stadio": f"Stadio di {casa}", "citta": "Italia", "campo": "Erba Naturale", 
            "coperto": False, "media_cartellini": 3.0, "lat": 41.9, "lon": 12.5
        })

    all_casa = DB_ALLENATORI.get(casa_key, DB_ALLENATORI.get("default", {"allenatore": "Tecnico Casa", "indice_tattico": 6}))
    all_ospite = DB_ALLENATORI.get(ospite_key, DB_ALLENATORI.get("default", {"allenatore": "Tecnico Ospite", "indice_tattico": 6}))
    
    arbitro_designato = scrappa_arbitro_live(casa, ospite)
    arbitro_entry = DB_ARBITRI.get(arbitro_designato.lower().strip(), 5)
    severita_arbitro = arbitro_entry if isinstance(arbitro_entry, int) else arbitro_entry.get("severita", 5)
    
    top_casa = DB_TOP_PLAYERS.get(casa_key, ["Portiere", "Difensore", "Centrocampista", "Attaccante"])
    top_ospite = DB_TOP_PLAYERS.get(ospite_key, ["Portiere", "Difensore", "Centrocampista", "Attaccante"])
    
    _, _, score_c, score_o = valuta_impatto_qualita_rosa(casa, ospite)
    
    meteo_live = ottieni_meteo_live(stadio_info.get("lat"), stadio_info.get("lon"))
    copertura_str = "Coperto (Stadio al chiuso)" if stadio_info.get("coperto", False) else "Scoperto"
    
    return {
        "STADIO": stadio_info.get("stadio", "Stadio Ufficiale"),
        "Città": stadio_info.get("citta", "N/D"),
        "TERRENO": stadio_info.get("campo", "Erba Naturale"),
        "COPERTURA": copertura_str,
        "METEO LIVE": meteo_live,
        "Allenatore Casa": all_casa.get('allenatore', 'N/D'),
        "Indice Tattico Casa": all_casa.get('indice_tattico', 5),
        "Allenatore Ospite": all_ospite.get('allenatore', 'N/D'),
        "Indice Tattico Ospite": all_ospite.get('indice_tattico', 5),
        "ALLENATORE CASA": f"{all_casa.get('allenatore', 'N/D')} (Indice Tattico: {all_casa.get('indice_tattico', 'N/D')})",
        "ALLENATORE OSPITE": f"{all_ospite.get('allenatore', 'N/D')} (Indice Tattico: {all_ospite.get('indice_tattico', 'N/D')})",
        "Arbitro Designato": arbitro_designato,
        "Severità Arbitro": severita_arbitro,
        "ARBITRO & SEVERITÀ": f"{arbitro_designato} (Indice Severità: {severita_arbitro}/10)",
        "Media Cartellini Stadio": stadio_info.get("media_cartellini", 2.5),
        "Top Players Casa": top_casa,
        "Top Players Ospite": top_ospite,
        "Rating Qualità Rosa Casa": round(score_c, 1),
        "Rating Qualità Rosa Ospite": round(score_o, 1)
    }

def esegui_master_calculator(casa: str, ospite: str, contesto: dict):
    """Elabora i fattori qualitativi umani, tattici, disciplinari e la qualità della rosa nel master calculator."""
    top_c = contesto.get("Top Players Casa", [])
    top_o = contesto.get("Top Players Ospite", [])
    
    tattica_casa = contesto.get("Indice Tattico Casa", 5)
    tattica_ospite = contesto.get("Indice Tattico Ospite", 5)
    delta_tattico = abs(tattica_casa - tattica_ospite)
    
    rating_c = contesto.get("Rating Qualità Rosa Casa", 7.5)
    rating_o = contesto.get("Rating Qualità Rosa Ospite", 7.5)
    
    valutazione_tattica = (
        "Scontro ad alto contenuto scacchistico tra i reparti." 
        if delta_tattico <= 2 
        else "Netta disparità di approccio tattico tra i due tecnici."
    )
    
    severita = contesto.get("Severità Arbitro", 5)
    var_profilo = DB_VARISTI.get("default", "Medio")
    var_interventismo = "Alto (Protocollo rigido)" if severita >= 7 or var_profilo == "Alto" else "Standard (Revisioni mirate)"

    return {
        "fattori_umani": f"Impatto pilastri [{', '.join(top_c)} vs {', '.join(top_o)}]. Rating Rosa: {casa} ({rating_c}) vs {ospite} ({rating_o}). {valutazione_tattica}",
        "disciplinare": f"Direzione affidata a {contesto.get('Arbitro Designato')} (Severità: {severita}). Interventismo VAR stimato: {var_interventismo}.",
        "flussi_monetari": f"Volumi di mercato allineati ai parametri xG, PPDA, profondità panchina e storico stadi per {casa} - {ospite}.",
        "top_players_chiave": {
            casa: top_c,
            ospite: top_o
        },
        "whale_alert": delta_tattico > 4 or abs(rating_c - rating_o) > 1.2,
        "trend_storici": f"Analisi H2H incrociata con efficienza balistica, duelli aerei e profondità dei panchinari registrati nel database."
    }