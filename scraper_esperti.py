# scraper_esperti.py
import sqlite3
import requests
from bs4 import BeautifulSoup

DB_NAME = 'esperti.db'

def salva_nel_db(match_id, fonte, valore):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO pronostici (match_id, fonte, valore, timestamp)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (match_id, fonte, valore))
    conn.commit()
    conn.close()

def scrape_il_veggente(match_id):
    url = f"https://www.ilveggente.it/partita/{match_id}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        indicatori = ["1", "x", "2", "multigol", "over", "under", "gol", "combo", "vittoria"]
        tag_candidati = soup.find_all(["b", "strong"])
        for tag in tag_candidati:
            testo = tag.text.lower().strip()
            if any(ind in testo for ind in indicatori) and len(testo) < 30:
                return tag.text.strip()
        return "N/D"
    except: return "Errore"

def scrape_metlive(match_id):
    # Metlive: cerchiamo la classe alert-success
    url = f"https://www.metlive.it/partita/{match_id}" # Aggiorna con l'URL corretto
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Cerchiamo il div con classe alert-success
        div = soup.find("div", class_="alert-success")
        if div:
            # Estraiamo il contenuto del tag <b> all'interno del div
            b_tag = div.find("b")
            return b_tag.text.strip() if b_tag else "N/D"
        return "N/D"
    except: return "Errore"

def scrape_90min(match_id):
    # 90min: cerchiamo il paragrafo che contiene "Pronostico"
    url = f"https://www.90min.it/partita/{match_id}" # Aggiorna con l'URL corretto
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Cerchiamo il <p> che contiene la stringa "Pronostico"
        p_tag = soup.find("p", string=lambda s: s and "Pronostico" in s)
        if p_tag:
            # "Pronostico: 1 - Over 2,5" -> vogliamo solo quello dopo i due punti
            return p_tag.text.split(":")[-1].strip()
        return "N/D"
    except: return "Errore"

def aggiorna_dati_esperti(match_id):
    print(f"Aggiornamento ESPERTI in corso per: {match_id}")
    
    valore_veggente = scrape_il_veggente(match_id)
    salva_nel_db(match_id, "il_veggente", valore_veggente)
    
    valore_metlive = scrape_metlive(match_id)
    salva_nel_db(match_id, "metlive", valore_metlive)
    
    valore_90min = scrape_90min(match_id)
    salva_nel_db(match_id, "90min", valore_90min)
    
    print("Aggiornamento completato.")

if __name__ == "__main__":
    # Inserisci qui un match_id reale per testare
    aggiorna_dati_esperti("test-match")