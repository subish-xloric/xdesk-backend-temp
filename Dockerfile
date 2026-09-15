FROM python:3.13-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    ACCEPT_EULA=Y

WORKDIR /x_desk_backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        gnupg \
        libffi-dev \
        libfreetype6-dev \
        libjpeg62-turbo-dev \
        libmariadb-dev \
        libssl-dev \
        libxml2-dev \
        libxslt1-dev \
        pkg-config \
        unixodbc-dev \
        zlib1g-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p \
    /x_desk_backend/dm-desk-docs/confidential_docs/interview_candidate_profile \
    /x_desk_backend/dm-desk-docs/reports/daily \
    /x_desk_backend/dm-desk-docs/reports/daily_punch_in \
    /x_desk_backend/dm-desk-docs/reports/daily_work_hours \
    /x_desk_backend/dm-desk-docs/reports/monthly \
    /x_desk_backend/dm-desk-docs/reports/weekly

COPY requirements.txt /x_desk_backend/
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r requirements.txt

COPY . /x_desk_backend/

EXPOSE 8000

CMD ["gunicorn", "--config", "gunicorn-cfg.py", "pTracker.wsgi"]
