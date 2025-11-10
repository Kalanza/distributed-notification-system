import pika, json, time
from fastapi import FastAPI
from threading import Thread

app = FastAPI(title="Email Service")

def consume_email_queue():
    def callback(ch, method, properties, body):
        data = json.loads(body)
        print(f"[Email Service] Sending email to user {data['user_id']} using template {data['template_id']}")
        time.sleep(2)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    connection = pika.BlockingConnection(pika.ConnectionParameters(host="rabbitmq"))
    channel = connection.channel()
    channel.queue_declare(queue="email.queue", durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="email.queue", on_message_callback=callback)
    print("[Email Service] Waiting for messages...")
    channel.start_consuming()

@app.on_event("startup")
def startup_event():
    Thread(target=consume_email_queue, daemon=True).start()

@app.get("/health")
def health_check():
    return {"status": "ok"}
