FROM python:3.9-slim

WORKDIR /backend

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "fastapi_ai:app", "--host", "0.0.0.0", "--port", "5000"]
