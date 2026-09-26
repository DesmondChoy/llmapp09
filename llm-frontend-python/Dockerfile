FROM python:3.12-alpine3.24

RUN apk upgrade --no-cache

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m pip uninstall --yes pip

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
