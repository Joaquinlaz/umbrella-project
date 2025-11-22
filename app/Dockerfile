FROM python:3.9-slim

WORKDIR /app

# Copiamos las dependencias
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código (incluyendo los nuevos nombres)
COPY . .

# IMPORTANTE: Aquí usamos el nombre REAL de tu script de base de datos
RUN python create_db.py

EXPOSE 5000

# IMPORTANTE: Aquí usamos el nombre REAL de tu app principal
CMD ["python", "vulnerable_flask_app.py"]