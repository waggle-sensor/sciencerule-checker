FROM waggle/plugin-base:1.1.1-base

COPY . /app/
RUN pip3 install -r /app/requirements.txt

ENTRYPOINT ["python3", "/app/checker.py"]