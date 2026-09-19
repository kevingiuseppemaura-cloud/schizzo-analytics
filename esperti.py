import sqlite3
import os

def init_db():
    """Crea il database e la tabella se non esistono."""
    conn = sqlite3.connect('esperti.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pronostici (
            match_id TEXT, 
            fonte TEXT, 
            valore TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_tutti_esperti(match_id: str):
    """Legge i pronostici dal database locale."""
    # Assicuriamoci che la tabella esista prima di leggere
    init_db()
    
    conn = sqlite3.connect('esperti.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT fonte, valore FROM pronostici WHERE match_id = ?", (match_id,))
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return {
                "il_veggente": "In attesa di aggiornamento...",
                "90min": "In attesa di aggiornamento...",
                "metlive": "In attesa di aggiornamento..."
            }
        
        return {fonte: valore for fonte, valore in rows}
    except Exception as e:
        conn.close()
        return {"Status": "Errore", "Dettaglio": str(e)}