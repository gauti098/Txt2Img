from django.conf import settings
from datetime import datetime
import pika


def rabbitMQSendJob(queue_name,queue_message,durable=False):
    try:
        _connectionsS = pika.BlockingConnection(pika.ConnectionParameters(settings.RABBITMQ_HOST,settings.RABBITMQ_PORT,'/',settings.RABBITMQ_CREDS))
        if not _connectionsS or _connectionsS.is_closed:
            _connectionsS = pika.BlockingConnection(pika.ConnectionParameters(settings.RABBITMQ_HOST,settings.RABBITMQ_PORT,'/',settings.RABBITMQ_CREDS))
        channel = _connectionsS.channel()
        channel.queue_declare(queue=queue_name,durable=durable)
        channel.basic_publish(exchange='', routing_key=queue_name, body=queue_message)
        _connectionsS.close()
        print(f" [x] {datetime.now()} [x] RabbitMQ [x] Success [x] Job Sent [x] QueueName {queue_name}")
    except Exception as e:
        print(f" [x] {datetime.now()} [x] RabbitMQ [x] Error [x] QueueName {queue_name} [x] {e}")

