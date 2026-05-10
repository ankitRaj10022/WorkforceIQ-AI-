FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN addgroup --system workforceiq && adduser --system --ingroup workforceiq workforceiq

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/instance && chown -R workforceiq:workforceiq /app
USER workforceiq

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=3).read()"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "run:app"]
