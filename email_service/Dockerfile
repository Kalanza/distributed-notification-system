FROM python:3.11-slim

WORKDIR /app

# Copy shared folder first
COPY ./shared ./shared

# Copy the entire email_service directory
COPY ./email_service ./email_service

# Copy requirements and install
COPY ./email_service/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Set working directory to email_service
WORKDIR /app/email_service

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
