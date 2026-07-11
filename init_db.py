# init_db.py
import sqlite3

def init_db():
    conn = sqlite3.connect('esperti.db')
    cursor = conn.cursor()
    # Creiamo la tabella che conterrà i pronostici
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pronostici (
            match_id TEXT,
            fonte TEXT,
            valore TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (match_id, fonte)
        )
    ''')
    conn.commit()
    conn.close()
    print("Database 'esperti.db' creato con successo.")

if __name__ == "__main__":
    init_db()