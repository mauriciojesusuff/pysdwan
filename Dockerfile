# Usar a imagem oficial do Python 3.11
FROM python:3.11-slim

# Configurar diretório de trabalho dentro do container
WORKDIR /app

# Copiar o arquivo requirements.txt e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código da aplicação para dentro do container
COPY . .

# Expor a porta que a aplicação usa (ajuste conforme necessário)
EXPOSE 8000

# Comando para iniciar a aplicação (ajuste conforme necessário)
CMD ["python"]
