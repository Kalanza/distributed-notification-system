FROM python:3.11-slim

WORKDIR /app

# Copy shared folder first
COPY ./shared ./shared

# Copy the entire api_gateway directory
COPY ./api_gateway ./api_gateway

# Copy requirements and install
COPY ./api_gateway/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Set working directory to api_gateway
WORKDIR /app/api_gateway

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
