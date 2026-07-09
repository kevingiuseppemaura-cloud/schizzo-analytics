import requests
import time
import random
from bs4 import BeautifulSoup
from cachetools import TTLCache

# Cache configurata per scadere dopo 15 minuti (900 secondi)
# Memorizza fino a 50 match contemporaneamente
cache_quote = TTLCache(maxsize=50, ttl=900)

def get_quote_flashscore(match_id):
    # 1. Controllo immediato in cache
    if match_id in cache_quote:
        return cache_quote[match_id]
    
    # 2. Rate Limiting: attesa casuale tra 1 e 3 secondi per sembrare "umano"
    time.sleep(random.uniform(1.0, 3.0))
    
    url = f"https://www.flashscore.it/partita/{match_id}/#/quote/quota-finale/1x2"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return 1.90 # Fallback in caso di errore server
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # LOGICA DI ESTRAZIONE (Personalizzabile)
        # Qui punteremo a un elemento placeholder, poi lo raffineremo in base alla struttura HTML di Flashscore
        quota_elemento = soup.find("span", {"class": "odds-value"})
        
        quota = float(quota_elemento.text.replace(',', '.')) if quota_elemento else 1.90
        
        # 3. Salva in cache
        cache_quote[match_id] = quota
        return quota
        
    except Exception as e:
        print(f"Errore scraping per {match_id}: {e}")
        return 1.90