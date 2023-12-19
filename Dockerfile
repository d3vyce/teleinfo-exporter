FROM python:3.12-slim

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY src/ /opt/

CMD [ "python3", "/opt/teleinfo_exporter" ]
