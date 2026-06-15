FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/
EXPOSE 8000

# 🚀 SRE Multi-Process Execution:
# '&' diye worker.py ke background-e push kora hoyeche ar uvicorn ke foreground-e rakha hoyeche.
# Jodi API crash khay, puro pod restart nibe (K8s standard behavior)!
CMD ["sh", "-c", "PYTHONUNBUFFERED=1 python src/worker.py & uvicorn main:app --app-dir src --host 0.0.0.0 --port 8000"]