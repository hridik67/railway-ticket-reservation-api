from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from .models import TicketType

class PassengerCreate(BaseModel):
    name: str
    age: int = Field(..., ge=0)
    gender: str

class TicketOut(BaseModel):
    id: int
    passenger_id: int
    type: TicketType
    seat_no: Optional[int]
    rac_position: Optional[int]
    wait_position: Optional[int]
    booked_at: datetime
    canceled_at: Optional[datetime]

    class Config:
        orm_mode = True
