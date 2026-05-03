FROM python:3.11-slim

# Diretório de trabalho
WORKDIR /app

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY monitor.py .

# Roda a Brisa
CMD ["python", "-u", "monitor.py"]
