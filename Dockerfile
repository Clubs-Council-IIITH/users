# cache dependencies
FROM python:3.14-slim-slim AS python_cache
COPY --from=ghcr.io/astral-sh/uv:0.10 /uv /uvx /bin/
RUN apt-get update && apt-get install ldap-utils libsasl2-dev libldap2-dev -y

FROM python_cache AS dependencies

ENV UV_LINK_MODE=copy
ENV UV_PYTHON_DOWNLOADS=0
ENV UV_COMPILE_BYTECODE=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-install-project

# build and start
FROM python:3.14-slim AS build
EXPOSE 80
RUN apt-get update && apt-get install -y --no-install-recommends \
    libldap2 \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

COPY --from=dependencies /opt/venv /opt/venv
COPY . .

RUN strawberry export-schema main > schema.graphql
ENTRYPOINT [ "./entrypoint.sh" ]
