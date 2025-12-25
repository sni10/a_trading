# 📌 Базовый образ с Python 3.10
FROM python:3.12-slim

# 🧰 Установим системные зависимости для сборки TA-Lib
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    curl \
    gcc \
    make \
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

# 📁 Копируем весь проект в контейнер (опционально)
COPY . /app
WORKDIR /app

CMD [ "pytest", "-q", "tests/" ]
