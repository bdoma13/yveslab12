import connexion
from connexion import NoContent
import json
from datetime import datetime
import os
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_
from base import Base
from ticket_info import ticketInfo
from review_info import reviewInfo
from uuid import uuid1
import logging.config
import time
import yaml
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread 

yaml_file = "./openapi.yml"

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

DB_ENGINE = create_engine(f"mysql+pymysql://{app_config['datastore']['user']}:{app_config['datastore']['password']}@{app_config['datastore']['hostname']}:{app_config['datastore']['port']}/{app_config['datastore']['db']}")
Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)
logger.info(f"Connected to DB. Hostname:{app_config['datastore']['hostname']}, Port:{app_config['datastore']['port']}")

def search_ticket(start_timestamp, end_timestamp): 
 
    session = DB_SESSION() 

    start_timestamp_datetime = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S")
    end_timestamp_datetime = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M:%S")
 
    readings = session.query(ticketInfo).filter(and_(ticketInfo.date_created >=   
                                                  start_timestamp_datetime, ticketInfo.date_created < end_timestamp_datetime)) 
 
    results_list = [] 
 
    for reading in readings: 
        results_list.append(reading.to_dict()) 
 
    session.close() 
     
    logger.info("Query for ticket readings between %s and %s retuerns %d results" %  
                (start_timestamp_datetime, end_timestamp_datetime, len(results_list))) 
 
    return results_list, 200

def search_review(start_timestamp, end_timestamp): 
 
    session = DB_SESSION() 
    
    start_timestamp_datetime = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M:%S")
    end_timestamp_datetime = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M:%S")
   
 
    readings = session.query(reviewInfo).filter(and_(reviewInfo.date_created >=   
                                                  start_timestamp_datetime, reviewInfo.date_created < end_timestamp_datetime)) 
 
    results_list = [] 
 
    for reading in readings: 
        results_list.append(reading.to_dict()) 
 
    session.close() 
     
    logger.info("Query for review readings between %s and %s returns %d results" %  
                (start_timestamp_datetime, end_timestamp_datetime, len(results_list))) 
 
    return results_list, 200

def process_messages(): 
    """ Process event messages """ 
    current_retry = 0
    
    while current_retry < app_config["events"]["max_retries"]:
        try:
            hostname = "%s:%d" % (app_config["events"]["hostname"],   
                                app_config["events"]["port"]) 
            client = KafkaClient(hosts=hostname)
            topic = client.topics[str.encode(app_config["events"]["topic"])]
            consumer = topic.get_simple_consumer(consumer_group=b'event_group', 
                                                reset_offset_on_start=False, 
                                                auto_offset_reset=OffsetType.LATEST) 
            #current_retry = app_config["events"]["max_retries"]
            logger.info("Connected to Kafka")
            break
        except:
            logger.error("Connection to Kafka failed!")
            time.sleep(app_config["events"]["sleep"])
            current_retry += 1
     
    # Create a consume on a consumer group, that only reads new messages  
    # (uncommitted messages) when the service re-starts (i.e., it doesn't  
    # read all the old messages from the history in the message queue). 

 
    # This is blocking - it will wait for a new message 
    for msg in consumer: 
        msg_str = msg.value.decode('utf-8') 
        msg = json.loads(msg_str) 
        logger.info("Message: %s" % msg) 
 
        payload = msg["payload"] 
                 
        if msg["type"] == "ticket_info": # Change this to your event type 
                session = DB_SESSION()
                
                bp = ticketInfo(payload['ticket_num'],
                              payload['movie_title'],
                              payload['runtime'],
                              payload['price'],
                              payload['trace_id'])

                session.add(bp)

                session.commit()
                session.close()

                logger.debug(f"Received event ticket_info request with a trace id of {payload['trace_id']}")

            
        elif msg["type"] == "review_info": # Change this to your event type 
                session = DB_SESSION()

                bp = reviewInfo(payload['review_id'],
                               payload['movie_title'],
                               payload['gender'],
                               payload['age'],
                               payload['rating'],
                               payload['trace_id'])

                session.add(bp)

                session.commit()
                session.close()

                logger.debug(f"Received event review_info request with a trace id of {payload['trace_id']}")

 
        # Commit the new message as being read 
        consumer.commit_offsets()

def get_health():
    return 200

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", base_path="/storage", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    t1 = Thread(target=process_messages) 
    t1.setDaemon(True) 
    t1.start()
    app.run(port=8090)
