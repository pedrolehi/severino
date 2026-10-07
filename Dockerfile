# Dockerfile para from-scratch-multiagent (Hub Multi-Assistente Senac)
# Baseado no padrao de producao para OpenShift / IBM Cloud
FROM python:3.11-slim

WORKDIR /app

# Dependencias essenciais do sistema para compilar dependencias C/C++ se necessario
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia requirements primeiro para aproveitar o cache de camadas do Docker
COPY requirements.txt .

# Instala pacotes Python usando wheels pre-compilados
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --prefer-binary -r requirements.txt

# Remove compiladores para reduzir tamanho da imagem final
RUN apt-get purge -y gcc g++ && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copia o codigo-fonte da aplicacao
COPY . .

# Variaveis de ambiente para Python em container
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Ajuste de permissoes para compatibilidade com OpenShift (arbitrary UID pertencente ao GID 0)
RUN chgrp -R 0 /app && \
    chmod -R g=u /app

# Expoe a porta da aplicacao
EXPOSE 8000

# Usuario nao-root para compliance de seguranca
USER 1001

# Inicializa o servidor FastAPI com Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
