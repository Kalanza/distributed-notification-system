FROM python:3.11-slim

WORKDIR /app

# Copy shared folder first
COPY ./shared ./shared

# Copy the entire user_service directory
COPY ./user_service ./user_service

# Copy requirements and install
COPY ./user_service/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Set working directory to user_service
WORKDIR /app/user_service

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
