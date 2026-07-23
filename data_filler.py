# data_filler.py
import sqlite3
# Qui importeresti il tuo scraper attuale che scarica i dati
import scraper_esperti 

def get_match_context(home_name, away_name):
    conn = sqlite3.connect('esperti.db')
    cursor = conn.cursor()
    
    # Verifica se abbiamo già i dati per questa partita in 'partite'
    cursor.execute('''SELECT arbitri.nome, arbitri.indice_severita 
                      FROM partite 
                      JOIN arbitri ON partite.arbitro_id = arbitri.id
                      WHERE partite.home_id = (SELECT id FROM squadre WHERE nome=?)''', (home_name,))
    
    data = cursor.fetchone()
    
    # SE NON ABBIAMO I DATI, ATTIVIAMO LO SCRAPER
    if not data:
        print(f"Dati non trovati per {home_name} vs {away_name}. Avvio auto-fill...")
        scraper_esperti.esegui_scraping_specifico(home_name, away_name)
        # Dopo lo scraping, ricarichiamo i dati dal DB
        cursor.execute(...) # Riprova la query
        data = cursor.fetchone()
        
    conn.close()
    return data # Ritorna il contesto per weights.py