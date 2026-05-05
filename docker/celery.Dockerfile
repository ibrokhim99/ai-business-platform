FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi==0.111.0 pydantic==2.7.1 pydantic-settings==2.2.1 \
    sqlalchemy==2.0.30 asyncpg==0.29.0 psycopg2-binary==2.9.9 \
    python-jose[cryptography]==3.3.0 passlib[bcrypt]==1.7.4 \
    redis[hiredis]==5.0.4 celery==5.4.0 flower==2.0.1 \
    numpy==1.26.4 scipy==1.13.0 scikit-learn==1.4.2 \
    structlog==24.1.0 python-dotenv==1.0.1 orjson==3.10.3

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["celery", "-A", "app.tasks.celery_app", "worker", "-l", "INFO", "-Q", "training,default"]
