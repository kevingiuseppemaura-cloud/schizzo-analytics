# init_db.py
import sqlite3

def init_db():
    conn = sqlite3.connect('esperti.db')
    # Abilitiamo le foreign keys per mantenere l'integrità dei dati
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # --- 1. TABELLE STRUTTURALI (Core Engine) ---
    
    # Squadre
    cursor.execute('''CREATE TABLE IF NOT EXISTS squadre (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT UNIQUE,
                        abitudine_erba TEXT)''') 

    # Giocatori (Gestione infortuni/squalifiche qui)
    cursor.execute('''CREATE TABLE IF NOT EXISTS giocatori (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT,
                        squadra_id INTEGER,
                        stato TEXT DEFAULT 'ok',
                        ruolo TEXT,
                        FOREIGN KEY(squadra_id) REFERENCES squadre(id))''')

    # Arbitri (Severità)
    cursor.execute('''CREATE TABLE IF NOT EXISTS arbitri (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT UNIQUE,
                        indice_severita REAL)''')

    # Stadi (Tipo erba/Condizione)
    cursor.execute('''CREATE TABLE IF NOT EXISTS stadi (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT UNIQUE,
                        tipo_erba TEXT,
                        condizione TEXT)''')

    # --- 2. TABELLE FLUSSO (Il tuo materiale esistente) ---

    # Tabella dei Pronostici
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pronostici (
            match_id TEXT,
            fonte TEXT,
            valore TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (match_id, fonte)
        )
    ''')

    # Tabella Orchestratore[cite: 1]
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS partite_attive (
            match_id TEXT PRIMARY KEY,
            kickoff DATETIME,
            status TEXT DEFAULT 'PENDING',
            context_data TEXT,
            risultato_finale TEXT,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --- 3. TABELLA RELAZIONALE (Collega tutto) ---
    
    # Colleghiamo gli elementi della partita all'orchestratore
    cursor.execute('''CREATE TABLE IF NOT EXISTS partite (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        match_id TEXT UNIQUE,
                        home_id INTEGER,
                        away_id INTEGER,
                        stadio_id INTEGER,
                        arbitro_id INTEGER,
                        FOREIGN KEY(match_id) REFERENCES partite_attive(match_id),
                        FOREIGN KEY(home_id) REFERENCES squadre(id),
                        FOREIGN KEY(away_id) REFERENCES squadre(id),
                        FOREIGN KEY(stadio_id) REFERENCES stadi(id),
                        FOREIGN KEY(arbitro_id) REFERENCES arbitri(id))''')

    conn.commit()
    conn.close()
    print("Database 'esperti.db' integrato e inizializzato con successo.")

if __name__ == "__main__":
    init_db()