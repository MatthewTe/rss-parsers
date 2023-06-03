FROM python:3.11-slim-buster

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv  ${VIRTUAL_ENV}
ENV PATH="${VIRTUAL_ENV}/bin:$PATH"

COPY requirements.txt . 
COPY ingest_articles.py /app/

RUN pip install --upgrade pip && \
    apt-get update && \
    apt-get install -y default-mysql-server default-libmysqlclient-dev gcc && \
    pip install -r requirements.txt

WORKDIR /app

CMD ["python", "ingest_articles.py"]


