FROM python:3.11

LABEL maintainer="Stefan Schlipfinger <stefan.schlipfinger@gmail.com>"

COPY . /app
WORKDIR /app/

RUN pip install --no-cache-dir -r /app/requirements.txt

CMD ["python3","/app/sma2mqtt.py"]
