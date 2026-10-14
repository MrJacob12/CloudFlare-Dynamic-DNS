FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UPDATE_INTERVAL=300

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY __main__.py docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "__main__.py"]