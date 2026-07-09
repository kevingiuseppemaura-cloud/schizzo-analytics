import asyncio
import random

# Questa è la struttura base che utilizzeremo.
# Per ora, simuliamo il recupero dati. 
# Quando saremo pronti, sostituiremo i 'return' con le chiamate vere.

async def get_veggente_insight(match_id: str):
    # Qui inseriremo la logica di scraping per ilveggente.it
    await asyncio.sleep(0.5) # Simula latenza rete
    return "Over 2.5"

async def get_90min_insight(match_id: str):
    # Qui inseriremo la logica di scraping per 90min.com
    await asyncio.sleep(0.5)
    return "Segno 1"

async def get_metlive_insight(match_id: str):
    # Qui inseriremo la logica di scraping per metlive.it
    await asyncio.sleep(0.5)
    return "GOL/GOL"

async def get_tutti_esperti(match_id: str):
    """
    Esegue tutte le chiamate in parallelo per velocità massima.
    """
    results = await asyncio.gather(
        get_veggente_insight(match_id),
        get_90min_insight(match_id),
        get_metlive_insight(match_id)
    )
    
    return {
        "il_veggente": results[0],
        "90min": results[1],
        "metlive": results[2]
    }