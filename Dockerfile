# 📌 Базовый образ с Python 3.12
FROM python:3.12-slim

# 🧰 Установим системные зависимости для сборки TA-Lib + PostgreSQL клиент
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    gcc \
    make \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 🧱 Установка TA-Lib из исходников
RUN apt-get update && apt-get install -y \
    wget \
    gcc \
    make \
    build-essential \
    && \
    wget https://github.com/TA-Lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz && \
    tar -xzf ta-lib-0.6.4-src.tar.gz && \
    cd ta-lib-0.6.4 && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib-0.6.4 ta-lib-0.6.4-src.tar.gz

# 🔧 Установка Python-зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 📁 Копируем весь проект в контейнер
COPY . /app
WORKDIR /app

# 🚀 Entrypoint: автоматические миграции при старте
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD [ "pytest", "-q", "tests/" ]
