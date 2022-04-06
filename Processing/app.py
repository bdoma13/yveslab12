from logging.handlers import BufferingHandler
import connexion
from connexion import NoContent
import requests
import swagger_ui_bundle
import yaml
import logging
import logging.config
from flask_cors import CORS, cross_origin
from apscheduler.schedulers.background import BackgroundScheduler
from base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from stats import Stats
from datetime import datetime
from uuid import uuid1
import os


yaml_file = "./openapi.yml"
url = 'http://localhost:8100'

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

DB_ENGINE = create_engine("sqlite:///%s" % app_config["datastore"]["filename"]) 
Base.metadata.bind = DB_ENGINE 
DB_SESSION = sessionmaker(bind=DB_ENGINE) 


import sqlite3 

if not os.path.exists(app_config["datastore"]["filename"]):
    conn = sqlite3.connect(app_config["datastore"]["filename"]) 

    c = conn.cursor() 
    c.execute(''' 
            CREATE TABLE stats 
            (id INTEGER PRIMARY KEY ASC,  
            num_of_review INTEGER NOT NULL, 
            avg_age FLOAT NOT NULL, 
            avg_rating FLOAT NOT NULL, 
            total_sale FLOAT NOT NULL, 
            num_of_ticket INTEGER NOT NULL, 
            last_updated VARCHAR(100) NOT NULL) 
            ''')
    c.execute(''' 
            INSERT INTO stats(
            num_of_review, 
            avg_age, 
            avg_rating, 
            total_sale, 
            num_of_ticket, 
            last_updated)
            VALUES(0,0,0,0, '1000-01-01 01:00:00'); 
            ''') 

    conn.commit() 
    conn.close() 


def populate_stats(): 
    """ Periodically update stats """ 
    logger.info(f"Periodic Request Process Has Started")

    timestamp_now = datetime.now()
    timestamp_now_str = timestamp_now.strftime("%Y-%m-%dT%H:%M:%S")
    session = DB_SESSION() 
    try:
        readings = session.query(Stats).order_by(Stats.last_updated.desc()).first()

        # results = [] 

        # for reading in readings: 
        #     results.append(reading.to_dict())
        results = readings.to_dict()["last_updated"].replace(microsecond=0)
    except:
        results = '0001-01-01 01:01:01'
    
    # print(results)
    review_url = f"{app_config['eventstore']['url']}/movie/review?start_timestamp={results}&end_timestamp={timestamp_now_str}"
    ticket_url = f"{app_config['eventstore']['url']}/movie/ticket?start_timestamp={results}&end_timestamp={timestamp_now_str}"
    review_res = requests.get(review_url)
    ticket_res = requests.get(ticket_url)
    review = review_res.json()
    ticket = ticket_res.json()
    if len(review) != 0 or len(ticket) != 0:
        responses = len(review) + len(ticket)

        if review_res.ok and ticket_res.ok:
            logger.info(f"Total responses received: {responses}")
        else:
            logger.error("GET request failed.")

        trace_id = str(uuid1())

        avg_age_view = sum([x['age'] for x in review])/len(review)
        avg_rating_view = sum([x['rating'] for x in review])/len(review)
        total_sale_ticket = sum([x['price'] for x in ticket])/len(ticket)

        logger.debug(f"Total number of reviews: {len(review)}. TraceID: {trace_id}")
        logger.debug(f"Average age of reviewers: {avg_age_view}. TraceID: {trace_id}")
        logger.debug(f"Average rating of reviews: {avg_rating_view}. TraceID: {trace_id}")
        logger.debug(f"Total sales: {total_sale_ticket}. TraceID: {trace_id}")
        logger.debug(f"Total number of ticket sold: {len(ticket)}. TraceID: {trace_id}")

        stats = Stats(len(review), 
                avg_age_view, 
                avg_rating_view, 
                total_sale_ticket, 
                len(ticket), 
                datetime.now())

        session.add(stats) 
        logger.debug(f"New Stat entry. TraceID: {trace_id}")
        session.commit()

    session.close()

    logger.info(f"Periodic Request Process has ended.")


def get_stats():
    logger.info("request for statistics received")
 
    session = DB_SESSION() 

    results = session.query(Stats).order_by(Stats.last_updated.desc()) 
    
    results_list = [] 
    
    if results:
        for reading in results: 
            results_list.append(reading.to_dict()) 
    
    session.close()
    
    newest_list = results_list[0]
    logger.debug(f"Statistics contents{newest_list}")
    logger.info("statistics request has been fulfilled")

    return results, 200


def init_scheduler():
    sched = BackgroundScheduler(daemon=True) 
    sched.add_job(populate_stats,'interval',seconds=app_config['scheduler']['period_sec']) 
    sched.start()

app = connexion.FlaskApp(__name__, specification_dir='')
CORS(app.app)
if "TARGET_ENV" not in os.environ or os.environ["TARGET_ENV"] != "test":
    CORS(app.app)
    app.app.config['CORS_HEADERS'] = 'Content-Type'
app.add_api(yaml_file, strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    init_scheduler() 
    app.run(port=8100, use_reloader=False)