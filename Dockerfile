FROM python:3.10.4-alpine3.15

# Create user
RUN adduser -D speedtest

WORKDIR /app
COPY src/requirements.txt .

# Install required modules
RUN apk update && \
    apk add make build-base && \
    pip install --no-cache -r requirements.txt && \
    apk del make build-base && \
    rm -rf /var/cache/apk/* && \
    find /usr/local/lib/python3.10 -name "*.pyc" -type f -delete

RUN apk add git && \
    git clone https://github.com/martinbrose/fastcli.git && \
    cd fastcli && \
    git checkout dev && \
    pip install -e . --no-cache-dir && \
    cd .. && \
    apk del git && \
    rm -rf /var/cache/apk/* && \
    find /usr/local/lib/python3.10 -name "*.pyc" -type f -delete    

COPY src/. .

USER speedtest

CMD ["python", "-u", "exporter.py"]

HEALTHCHECK --timeout=10s CMD wget --no-verbose --tries=1 --spider http://localhost:${SPEEDTEST_PORT:=9798}/
