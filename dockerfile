FROM python:3.9

WORKDIR /usr/src/app
ENV PYTHONPATH=/usr/src/app
COPY . .


RUN pip install --no-cache-dir -r requirements.txt


CMD ["sh", "-c", "alembic upgrade head && python3 app.py & python3 tasks/update_telegram_config.py"]
