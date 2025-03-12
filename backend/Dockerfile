FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

CMD ["bash", "-c", "python manage.py migrate && python /app/load_data.py && gunicorn --bind 0.0.0.0:8080 foodgram_project.wsgi"]