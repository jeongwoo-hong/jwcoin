FROM python:3.11-slim

WORKDIR /app

RUN pip install flask

COPY test_app.py .

ENV PORT=8080
EXPOSE 8080

CMD ["python", "test_app.py"]