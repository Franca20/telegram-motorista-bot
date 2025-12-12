FROM python:3.10-slim

# Criar diretório de trabalho
WORKDIR /app

# Copiar arquivos
COPY requirements.txt .
COPY main.py .
COPY estrutura.py .
COPY planilha_fechamento.py .
COPY gerenciador_usuarios.py .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Rodar o bot
CMD ["python", "main.py"]
