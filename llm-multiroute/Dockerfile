FROM python:3.12-alpine3.24

RUN apk upgrade --no-cache

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Package installation (including Guardrails Hub installs) belongs at build time.
# pip bundles vulnerable libraries that are not needed to serve requests.
RUN python -m pip uninstall --yes pip

COPY . .

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
