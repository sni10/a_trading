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

# 🐍 Установка Poetry
ENV POETRY_VERSION=2.1.3 \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /opt/poetry/bin/poetry /usr/local/bin/poetry

# 📁 Копируем файлы зависимостей и устанавливаем
WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --no-directory

# 📁 Копируем весь проект в контейнер
COPY . /app
RUN poetry install --no-root

# 🚀 Entrypoint: автоматические миграции при старте
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD [ "pytest", "-q", "tests/" ]
