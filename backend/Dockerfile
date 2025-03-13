FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

RUN mkdir -p foodgram/data

COPY ../data/ingredients.csv foodgram/data/

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "foodgram_project.wsgi"]