FROM python:3-alpine

EXPOSE 9709

# The actual exporter
COPY float_exporter.py /usr/local/bin/

COPY requirements.txt .
RUN pip install --requirement requirements.txt

ENTRYPOINT [ "python", "/usr/local/bin/float_exporter.py" ]
