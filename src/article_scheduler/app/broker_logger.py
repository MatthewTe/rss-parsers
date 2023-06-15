import datetime
from pythonjsonlogger import jsonlogger
import os 
import logging
from python_logging_rabbitmq import RabbitMQHandler

# Logging config:
APP_NAME = "scheduler"

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname


logger = logging.getLogger(APP_NAME)
logger.setLevel(logging.DEBUG)

rabbit = RabbitMQHandler(
	host=os.environ.get("BROKER_URL", "localhost"),
	port=5672,
    exchange="amq.topic",
	username='guest',
	password='guest',
    formatter=CustomJsonFormatter(),
	connection_params={
		'virtual_host': '/',
		'connection_attempts': 3,
		'socket_timeout': 5000
	},
    fields={"source":f"{APP_NAME}-producer"},
    fields_under_root=True
)

logger.addHandler(rabbit)

