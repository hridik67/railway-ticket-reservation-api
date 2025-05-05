FROM python:3.11-slim

WORKDIR /app

# 1. Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Copy application code and the wait script
COPY railway_ticket_reservation_app ./railway_ticket_reservation_app
COPY .env .
COPY wait-for-it.sh .

# 3. Make wait-for-it executable (in case Windows permissions didn’t carry over)
RUN chmod +x wait-for-it.sh

# 4. Start: wait for `db:5432` then launch uvicorn
CMD ["./wait-for-it.sh", "db:5432", "--", \
     "uvicorn", "railway_ticket_reservation_app.main:app", \
     "--host", "0.0.0.0", "--port", "8000"]
