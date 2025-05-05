from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, text
from fastapi import HTTPException
from . import models, schemas
from .models import TicketType
from sqlalchemy.exc import DBAPIError

# constants
MAX_CONFIRMED = 63
MAX_RAC       = 18
MAX_WAIT      = 10

def init_counters(db: Session):
    if not db.execute(select(models.Counters)).scalar_one_or_none():
        db.add(models.Counters())
        db.commit()

def book_ticket(db: Session, passenger_in: schemas.PassengerCreate):
    # wrap all in a transaction
    try:
        with db.begin():
            # lock counters row
            counters = db.execute(
                select(models.Counters).with_for_update()
            ).scalar_one()
            # create passenger
            p = models.Passenger(**passenger_in.dict())
            db.add(p)
            db.flush()  # get p.id

            # children under 5: store as child, no seat consumed
            if p.age < 5:
                t = models.Ticket(passenger_id=p.id, type=TicketType.child)
                db.add(t)
                return t

            # count current confirmed & rac & waiting
            confirmed_ct = db.scalar(select(func.count()).select_from(models.Ticket).where(
                models.Ticket.type == TicketType.confirmed))
            rac_ct       = db.scalar(select(func.count()).select_from(models.Ticket).where(
                models.Ticket.type == TicketType.rac))
            wait_ct      = db.scalar(select(func.count()).select_from(models.Ticket).where(
                models.Ticket.type == TicketType.waiting))

            if confirmed_ct < MAX_CONFIRMED:
                seat_no = counters.confirmed_next_seat
                counters.confirmed_next_seat += 1
                t = models.Ticket(
                    passenger_id=p.id,
                    type=TicketType.confirmed,
                    seat_no=seat_no
                )
            elif rac_ct < MAX_RAC:
                pos = counters.rac_next_position
                counters.rac_next_position += 1
                t = models.Ticket(
                    passenger_id=p.id,
                    type=TicketType.rac,
                    rac_position=pos
                )
            elif wait_ct < MAX_WAIT:
                pos = counters.wait_next_position
                counters.wait_next_position += 1
                t = models.Ticket(
                    passenger_id=p.id,
                    type=TicketType.waiting,
                    wait_position=pos
                )
            else:
                raise HTTPException(400, "No tickets available")
            db.add(t)
            return t
    except DBAPIError as e:
        raise HTTPException(500, "Database error")

def cancel_ticket(db: Session, ticket_id: int):
    try:
        with db.begin():
            # lock counters to serialize
            db.execute(select(models.Counters).with_for_update()).scalar_one()
            t = db.get(models.Ticket, ticket_id)
            if not t or t.canceled_at:
                raise HTTPException(404, "Ticket not found or already canceled")
            t.canceled_at = func.now()
            typ = t.type
            # if confirmed, promote RAC → confirmed, then waiting → RAC
            if typ == TicketType.confirmed:
                # next RAC
                next_rac = db.scalar(select(models.Ticket)
                    .where(models.Ticket.type==TicketType.rac)
                    .order_by(models.Ticket.rac_position)
                    .limit(1))
                if next_rac:
                    next_rac.type = TicketType.confirmed
                    next_rac.seat_no = t.seat_no
                    next_rac.rac_position = None
                    # shift up remaining RAC positions
                    db.execute(text("""
                        UPDATE tickets SET rac_position = rac_position - 1
                         WHERE type='rac' AND rac_position > :pos
                    """), {"pos": next_rac.rac_position})
                    # one waiting to RAC
                    next_wait = db.scalar(select(models.Ticket)
                        .where(models.Ticket.type==TicketType.waiting)
                        .order_by(models.Ticket.wait_position)
                        .limit(1))
                    if next_wait:
                        next_wait.type = TicketType.rac
                        next_wait.rac_position = MAX_RAC
                        next_wait.wait_position = None
                        # shift up waiting positions
                        db.execute(text("""
                            UPDATE tickets SET wait_position = wait_position - 1
                             WHERE type='waiting' AND wait_position > :wpos
                        """), {"wpos": next_wait.wait_position})
            elif typ == TicketType.rac:
                # vacancy in RAC → pull first waiting
                next_wait = db.scalar(select(models.Ticket)
                    .where(models.Ticket.type==TicketType.waiting)
                    .order_by(models.Ticket.wait_position)
                    .limit(1))
                if next_wait:
                    next_wait.type = TicketType.rac
                    next_wait.rac_position = t.rac_position
                    # shift rac and waiting
                    db.execute(text("""
                        UPDATE tickets SET rac_position = rac_position - 1
                         WHERE type='rac' AND rac_position > :pos
                    """), {"pos": t.rac_position})
                    db.execute(text("""
                        UPDATE tickets SET wait_position = wait_position - 1
                         WHERE type='waiting' AND wait_position > :wpos
                    """), {"wpos": next_wait.wait_position})
            # if waiting: just mark canceled
            return {"message": "Canceled"}
    except DBAPIError:
        raise HTTPException(500, "DB error during cancellation")
