from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, func
from sqlalchemy.orm import relationship
from .database import Base
import enum

class TicketType(enum.Enum):
    confirmed = "confirmed"
    rac       = "rac"
    waiting   = "waiting"
    child     = "child"

class Passenger(Base):
    __tablename__ = "passengers"
    id      = Column(Integer, primary_key=True, index=True)
    name    = Column(String, nullable=False)
    age     = Column(Integer, nullable=False)
    gender  = Column(String(10), nullable=False)
    tickets = relationship("Ticket", back_populates="passenger", cascade="all, delete")

class Ticket(Base):
    __tablename__ = "tickets"
    id            = Column(Integer, primary_key=True, index=True)
    passenger_id  = Column(Integer, ForeignKey("passengers.id"), nullable=False)
    type          = Column(Enum(TicketType), nullable=False)
    seat_no       = Column(Integer, nullable=True)
    rac_position  = Column(Integer, nullable=True)
    wait_position = Column(Integer, nullable=True)
    booked_at     = Column(DateTime(timezone=True), server_default=func.now())
    canceled_at   = Column(DateTime(timezone=True), nullable=True)
    passenger     = relationship("Passenger", back_populates="tickets")

class Counters(Base):
    __tablename__ = "counters"
    id                   = Column(Integer, primary_key=True, default=1)
    confirmed_next_seat  = Column(Integer, default=1)
    rac_next_position    = Column(Integer, default=1)
    wait_next_position   = Column(Integer, default=1)
