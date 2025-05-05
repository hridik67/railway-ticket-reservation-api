from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from .models import Ticket, TicketType
from . import database, crud, schemas

app = FastAPI()

@app.on_event("startup")
def startup():
    # create tables & counters
    database.Base.metadata.create_all(bind=database.engine)
    db = next(database.get_db())
    crud.init_counters(db)

@app.post("/api/v1/tickets/book", response_model=schemas.TicketOut)
def book_ticket(passenger: schemas.PassengerCreate, db: Session = Depends(database.get_db)):
    return crud.book_ticket(db, passenger)

@app.post("/api/v1/tickets/cancel/{ticket_id}")
def cancel_ticket(ticket_id: int, db: Session = Depends(database.get_db)):
    return crud.cancel_ticket(db, ticket_id)

@app.get("/api/v1/tickets/booked", response_model=list[schemas.TicketOut])
def list_booked(db: Session = Depends(database.get_db)):
    # fetch all non-canceled tickets
    return (
        db.query(Ticket)
          .filter(Ticket.canceled_at.is_(None))
          .all()
    )

@app.get("/api/v1/tickets/available")
def list_available(db: Session = Depends(database.get_db)):
    confirmed = (
        db.query(Ticket)
          .filter(Ticket.type == TicketType.confirmed,
                  Ticket.canceled_at.is_(None))
          .count()
    )
    rac = (
        db.query(Ticket)
          .filter(Ticket.type == TicketType.rac,
                  Ticket.canceled_at.is_(None))
          .count()
    )
    waiting = (
        db.query(Ticket)
          .filter(Ticket.type == TicketType.waiting,
                  Ticket.canceled_at.is_(None))
          .count()
    )
    return {
        "confirmed_used": confirmed,
        "confirmed_free": crud.MAX_CONFIRMED - confirmed,
        "rac_used":       rac,
        "rac_free":       crud.MAX_RAC - rac,
        "waiting_used":   waiting,
        "waiting_free":   crud.MAX_WAIT - waiting
    }
