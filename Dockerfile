# cache dependencies
FROM python:3.11 as python_cache
RUN apt-get update && apt-get install libsasl2-dev python3-dev libldap2-dev libssl-dev slapd -y
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
WORKDIR /cache/
COPY requirements.txt .
RUN python -m venv /venv
RUN pip install -r requirements.txt
CMD ["sleep", "infinity"]

# build and start
FROM python:3.11-slim as build
EXPOSE 80
RUN apt-get update && apt-get install libldap-2.5.0 -y
WORKDIR /app
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
COPY --from=python_cache /venv /venv
COPY . .
RUN strawberry export-schema main > schema.graphql
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
