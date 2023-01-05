FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

EXPOSE 80

COPY . /app
RUN apt update && apt install libsasl2-dev python-dev libldap2-dev libssl-dev -y

RUN pip install -r requirements.txt
