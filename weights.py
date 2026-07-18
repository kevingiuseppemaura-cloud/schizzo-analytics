# weights.py

def get_context_multiplier(contesto):
    """
    contesto: dizionario con i dati (Meteo, Stadio, Motivazione, Mister, etc.)
    Ritorna un moltiplicatore unico da applicare alla Poisson.
    """
    
    # Base: 1.0 (neutro)
    moltiplicatore = 1.0
    
    # 1. PESO STADIO (Sintetico/Vero, Aperto/Chiuso)
    # Se il prato è sintetico e la squadra è abituata a quello vero, penalizziamo
    if contesto.get("stadio_tipo") == "sintetico" and contesto.get("squadra_abitudine") == "naturale":
        moltiplicatore *= 0.95
    if contesto.get("stadio_condizione") == "chiuso": # Effetto stadio chiuso/coperto
        moltiplicatore *= 1.02
        
    # 2. PESO MOTIVAZIONE (Scala 0.8 - 1.2)
    # Esempio: Alta (1.1), Normale (1.0), Scarsa (0.9)
    motivazione_map = {"alta": 1.1, "normale": 1.0, "scarsa": 0.9}
    moltiplicatore *= motivazione_map.get(contesto.get("motivazione", "normale"), 1.0)
    
    # 3. PESO MISTER (Basato su Punti per Partita o Performance)
    # Esempio: valore dato dal DB (es. 1.05 = Mister esperto, 0.95 = Mister in crisi)
    moltiplicatore *= contesto.get("peso_mister", 1.0)
    
    # 4. PESO INFORTUNI/SQUALIFICHE (Logica Yildiz/Lautaro)
    # Se mancano giocatori chiave, il moltiplicatore scende
    if contesto.get("giocatori_chiave_out", False):
        moltiplicatore *= 0.85
        
    # 5. PESO ARBITRO (Severità)
    # Se l'arbitro è severo (molti cartellini), penalizza la squadra che fa molti falli
    if contesto.get("arbitro_severo") and contesto.get("squadra_aggressiva"):
        moltiplicatore *= 0.92
        
    return moltiplicatore