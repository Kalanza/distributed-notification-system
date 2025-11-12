web: cd api_gateway && uvicorn main:app --host 0.0.0.0 --port $PORT
email_worker: cd email_service && python worker.py
push_worker: cd push_service && python worker.py
