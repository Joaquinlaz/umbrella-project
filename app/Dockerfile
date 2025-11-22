FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ejecutamos init_db una vez al construir para asegurar que la DB exista
RUN python init_db.py

EXPOSE 5000

CMD ["python", "app.py"]