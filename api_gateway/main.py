import pika, json, uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from shared.schemas.notification_schema import NotificationPayload

app = FastAPI(title="API Gateway")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/notifications/send")
def send_notification(payload: NotificationPayload):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
        channel = connection.channel()

        channel.exchange_declare(exchange='notifications.direct', exchange_type='direct')

        queue = f"{payload.channel}.queue"
        channel.queue_declare(queue=queue, durable=True)
        channel.queue_bind(exchange='notifications.direct', queue=queue, routing_key=payload.channel)

        message = json.dumps(payload.dict())
        channel.basic_publish(
            exchange='notifications.direct',
            routing_key=payload.channel,
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,  # persistent message
                message_id=str(uuid.uuid4())
            )
        )
        connection.close()
        return {"success": True, "message": f"Notification queued for {payload.channel}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
