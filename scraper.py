import requests
from bs4 import BeautifulSoup

def estrai_arbitro(url_o_match_data):
    """
    Esegue lo scraping per rilevare l'arbitro designato per la partita.
    Restituisce il nome dell'arbitro oppure 'ND' se non ancora designato o non trovato.
    """
    try:
        # Richiesta HTTP alla pagina del match monitorata
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url_o_match_data, headers=headers, timeout=5)
        
        if response.status_code != 200:
            return "ND"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Selettore del campo arbitro (adattabile alla struttura HTML di riferimento)
        elemento_arbitro = soup.find("span", {"id": "match-referee"})
        
        if not elemento_arbitro:
            return "ND"
            
        nome_arbitro = elemento_arbitro.get_text(strip=True)
        
        # Validazione della stringa estratta
        if not nome_arbitro or "da definire" in nome_arbitro.lower() or "nd" == nome_arbitro.lower():
            return "ND"
            
        return nome_arbitro
        
    except Exception:
        # Fallback di sicurezza in caso di eccezioni di rete o parsing
        return "ND"

def process_arbitro_per_calcolo(url_match, database_arbitri):
    """
    Funzione di raccordo che gestisce lo scraping e l'interrogazione del database:
    1. Cerca l'arbitro tramite scraping.
    2. Se restituisce 'ND', assegna il moltiplicatore neutro (1.0) senza influire su Poisson.
    3. Se trovato, preleva l'indice di severità dal database degli arbitri.
    """
    nome_arbitro = estrai_arbitro(url_match)
    
    if nome_arbitro == "ND" or not nome_arbitro:
        return {
            "arbitro": "ND",
            "moltiplicatore_arbitro": 1.0  # Valore neutro per preservare la precisione di Poisson
        }
    
    # Interrogazione del database arbitri (restituisce 1.0 di default se non censito)
    indice_severita = database_arbitri.get(nome_arbitro, 1.0)
    
    return {
        "arbitro": nome_arbitro,
        "moltiplicatore_arbitro": indice_severita
    }