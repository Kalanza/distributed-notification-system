FROM python:3.11-slim

WORKDIR /app

# Copy shared folder first
COPY ./shared ./shared

# Copy the entire push_service directory
COPY ./push_service ./push_service

# Copy requirements and install
COPY ./push_service/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Set working directory to push_service
WORKDIR /app/push_service

CMD ["python", "worker.py"]
