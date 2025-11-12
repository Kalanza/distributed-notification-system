FROM python:3.11-slim

WORKDIR /app

# Copy shared folder first
COPY ./shared ./shared

# Copy the entire template_service directory
COPY ./template_service ./template_service

# Copy requirements and install
COPY ./template_service/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Set working directory to template_service
WORKDIR /app/template_service

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
