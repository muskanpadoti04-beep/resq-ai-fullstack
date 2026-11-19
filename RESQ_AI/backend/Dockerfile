FROM python:3.12-slim
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
ENV RESQ_DB_PATH=/data/resqai.db
EXPOSE 8000
# seed only if the database does not exist yet, then start the API
CMD ["sh", "-c", "[ -f $RESQ_DB_PATH ] || python seed_database.py; uvicorn app.main:app --host 0.0.0.0 --port 8000"]
