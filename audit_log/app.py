import connexion
import swagger_ui_bundle
import pykafka
import yaml
import logging
import logging.config
import json
import os
from flask_cors import CORS, cross_origin
from pykafka import KafkaClient


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


def get_ticket(index): 
    """ Get Ticket Item in History """ 
    hostname = "%s:%d" % (app_config["events"]["hostname"],  
                          app_config["events"]["port"]) 
    client = KafkaClient(hosts=hostname) 
    topic = client.topics[str.encode(app_config["events"]["topic"])] 
 
    # Here we reset the offset on start so that we retrieve 
    # messages at the beginning of the message queue.  
    # To prevent the for loop from blocking, we set the timeout to 
    # 100ms. There is a risk that this loop never stops if the 
    # index is large and messages are constantly being received! 
    consumer = topic.get_simple_consumer(reset_offset_on_start=True,  
                                         consumer_timeout_ms=1000) 
 
    logger.info("Retrieving Ticket Item at index %d" % index) 
    try: 
        food_list = []
        for msg in consumer: 
            msg_str = msg.value.decode('utf-8') 
            msg = json.loads(msg_str) 
            
            if msg['type'] == "ticket_info":
                food_list.append(msg['payload'])
 
            # Find the event at the index you want and  
            # return code 200 
            # i.e., return event, 200 
                       
        if index < len(food_list):
            event = food_list[index]
            logger.info(f"Found Ticket Item at index {index} with Ticket number {event['ticket_num']}")
            return event, 200
        
    except: 
        logger.error("No more messages found") 
     
    logger.error("Could not find Ticket Item at index %d" % index) 
    return { "message": "Not Found"}, 404 


def get_review(index): 
    """ Get Review Item in History """ 
    hostname = "%s:%d" % (app_config["events"]["hostname"],  
                          app_config["events"]["port"]) 
    client = KafkaClient(hosts=hostname) 
    topic = client.topics[str.encode(app_config["events"]["topic"])] 
 
    # Here we reset the offset on start so that we retrieve 
    # messages at the beginning of the message queue.  
    # To prevent the for loop from blocking, we set the timeout to 
    # 100ms. There is a risk that this loop never stops if the 
    # index is large and messages are constantly being received! 
    consumer = topic.get_simple_consumer(reset_offset_on_start=True,  
                                         consumer_timeout_ms=1000) 
 
    logger.info("Retrieving review Item at index %d" % index) 
    try:
        drink_list = []
        for msg in consumer: 
            msg_str = msg.value.decode('utf-8') 
            msg = json.loads(msg_str) 
            
            if msg['type'] == "review_info":
                drink_list.append(msg['payload'])
 
            # Find the event at the index you want and  
            # return code 200 
            # i.e., return event, 200 
            
        if index < len(drink_list):
            event = drink_list[index]
            logger.info(f"Found Review Item at index {index} with Review ID {event['review_id']}")
            return event, 200
        
    except: 
        logger.error("No more messages found") 
     
    logger.error("Could not find Review Item at index %d" % index) 
    return {"message": "Not Found"}, 404 

def get_health():
    return 200

app = connexion.FlaskApp(__name__, specification_dir='')
CORS(app.app)
if "TARGET_ENV" not in os.environ or os.environ["TARGET_ENV"] != "test":
    CORS(app.app)
    app.app.config['CORS_HEADERS'] = 'Content-Type'
app.add_api("openapi.yml", base_path="/audit_log", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8110)
