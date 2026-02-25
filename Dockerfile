# cache dependencies
FROM python:3.13 AS python_cache
RUN apt-get update && apt-get install ldap-utils libsasl2-dev libldap2-dev -y

FROM python_cache AS dependencies
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /cache/
COPY requirements.txt .
RUN python -m venv /venv
RUN pip install -r requirements.txt

# build and start
FROM python:3.13-slim AS build
EXPOSE 80
RUN apt-get update && apt-get install -y --no-install-recommends \
    libldap2 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY --from=dependencies /venv /venv
COPY . .
RUN strawberry export-schema main > schema.graphql
ENTRYPOINT [ "./entrypoint.sh" ]
