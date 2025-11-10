FROM python:3.11-slim

WORKDIR /app

# Copy shared folder
COPY ./shared ./shared

# Copy service files (excluding Dockerfile)
COPY ./api_gateway/*.py ./
COPY ./api_gateway/requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
