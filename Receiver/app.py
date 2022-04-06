import connexion
from connexion import NoContent
import json
from datetime import datetime
import os
import requests
import yaml
import logging.config
from uuid import uuid1
import time
from pykafka import KafkaClient

url = 'http://localhost:8090'

if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"
    
with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())
    
# External Logging Configuration
with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

logger.info("App Conf File: %s" % app_conf_file)
logger.info("Log Conf File: %s" % log_conf_file)

current_retry = 0

while current_retry < app_config["events"]["max_retries"]:
    try:
        hostname = "%s:%d" % (app_config["events"]["hostname"],   
                            app_config["events"]["port"]) 
        client = KafkaClient(hosts=hostname)
        topic = client.topics[str.encode(app_config["events"]["topic"])]
        producer = topic.get_sync_producer() 
        current_retry = app_config["events"]["max_retries"]
        logger.info("Connected to Kafka")
    except:
        logger.error("Connection to Kafka failed!")
        time.sleep(app_config["events"]["sleep"])
        current_retry += 1

def ticket_info(body):
    """ Adds a new ticket information to the system """
    trace_id = str(uuid1())
    body['trace_id'] = trace_id

    msg = { "type": "ticket_info",  
            "datetime" :    
            datetime.now().strftime( 
                "%Y-%m-%dT%H:%M:%S"),  
            "payload": body } 
    msg_str = json.dumps(msg) 
    producer.produce(msg_str.encode('utf-8'))
    
    logger.info(f"ticketinfo added with {trace_id}")
    
    return NoContent , 201


def review_info(body):
    """ Adds a new review to the system """
    trace_id = str(uuid1())
    body['trace_id'] = trace_id

    msg = { "type": "review_info",  
            "datetime" :    
            datetime.now().strftime( 
                "%Y-%m-%dT%H:%M:%S"),  
            "payload": body } 
    msg_str = json.dumps(msg) 
    producer.produce(msg_str.encode('utf-8'))
    
    logger.info(f"review info added with {trace_id}")

    return NoContent, 201


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", base_path="/receiver", strict_validation=True, validate_responses=True)


if __name__ == "__main__":
    app.run(port=8080)
