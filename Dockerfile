# Usa imagem Python leve
FROM python:3.10-slim

# Evita arquivos de cache e logs presos
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências de sistema para OpenCV e Vídeo
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Instala as bibliotecas do requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia seu código para dentro do servidor
COPY . .

# Cria pasta temporária
RUN mkdir -p temp_files

# Porta padrão
EXPOSE 8000

# Comando de inicialização
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
