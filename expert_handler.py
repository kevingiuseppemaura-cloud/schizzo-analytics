import sqlite3
import os

DB_PATH = "esperti.db"

def get_expert_predictions(match_id):
    """
    Recupera i dati degli esperti per un determinato match_id in modo sicuro.
    Se il database non esiste o si verifica un errore, restituisce una struttura 
    di fallback per evitare di compromettere il backend principale.
    """
    if not os.path.exists(DB_PATH):
        return {
            "status": "error", 
            "message": "Database esperti non trovato", 
            "data": []
        }
    
    try:
        # Connessione al database SQLite
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Permette di accedere ai campi come dizionario
        cursor = conn.cursor()
        
        # Esecuzione della query filtrata per match_id
        # (Assicurati che la tabella e la colonna rispecchino la struttura del tuo DB)
        cursor.execute("SELECT * FROM experts WHERE match_id = ?", (match_id,))
        rows = cursor.fetchall()
        
        # Conversione dei risultati in una lista di dizionari
        experts_data = [dict(row) for row in rows]
        conn.close()
        
        if not experts_data:
            return {
                "status": "success", 
                "message": "Nessun esperto disponibile", 
                "data": []
            }
        
        return {
            "status": "success", 
            "message": "Dati caricati con successo", 
            "data": experts_data
        }
        
    except Exception as e:
        # Gestione degli errori isolata: il server non crollerà mai per un errore qui
        return {
            "status": "error", 
            "message": str(e), 
            "data": []
        }