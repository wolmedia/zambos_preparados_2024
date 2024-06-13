# Usa una imagen base de Python
FROM python:3.8-slim

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia el archivo requirements.txt al contenedor
COPY requirements.txt requirements.txt

# Instala las dependencias definidas en requirements.txt
RUN pip install -r requirements.txt

# Copia todo el contenido del directorio actual al contenedor en /app
COPY . .

EXPOSE 5199

# Define el comando a ejecutar cuando el contenedor se inicie
CMD ["python", "main.py"]
