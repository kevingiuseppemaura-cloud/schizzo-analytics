import pandas as pd
import json

# Carichiamo il file
df = pd.read_csv('serie_a_dati.csv')

def calcola_tutto():
    stats = {}

    for _, row in df.iterrows():
        # Dati casa e trasferta
        home, away = row['HomeTeam'], row['AwayTeam']
        
        # Inizializziamo le squadre
        for team in [home, away]:
            if team not in stats:
                stats[team] = {"gialli": 0, "rossi": 0, "falli": 0}
        
        # Sommiamo gialli, rossi e falli
        stats[home]["gialli"] += int(row['HY'])
        stats[home]["rossi"] += int(row['HR'])
        stats[home]["falli"] += int(row['HF'])
        
        stats[away]["gialli"] += int(row['AY'])
        stats[away]["rossi"] += int(row['AR'])
        stats[away]["falli"] += int(row['AF'])
        
    return stats

# Eseguiamo il calcolo
risultati = calcola_tutto()

# Salviamo in un formato pulito
with open('statistiche_complete.json', 'w') as f:
    json.dump(risultati, f, indent=4)

print("Fatto! Statistiche complete (Gialli, Rossi, Falli) salvate in 'statistiche_complete.json'.")