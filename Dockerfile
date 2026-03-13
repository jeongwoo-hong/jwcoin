FROM python:3.11-slim

WORKDIR /app

COPY requirements_dashboard.txt .
RUN pip install --no-cache-dir -r requirements_dashboard.txt

COPY dashboard.py .
COPY .streamlit .streamlit

EXPOSE 8501

CMD streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0 --server.headless true