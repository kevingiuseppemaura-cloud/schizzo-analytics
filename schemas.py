# schemas.py
from pydantic import BaseModel
from typing import Optional

class MatchRequest(BaseModel):
    match_id: Optional[str] = None
    squadra_casa: Optional[str] = None
    squadra_ospite: Optional[str] = None
    home: Optional[str] = None
    away: Optional[str] = None
    lambda_casa: Optional[float] = None
    lambda_ospite: Optional[float] = None
    moltiplicatore_infortuni: Optional[float] = 1.0
    moltiplicatore_stadio: Optional[float] = 1.0
    moltiplicatore_arbitro: Optional[float] = 1.0