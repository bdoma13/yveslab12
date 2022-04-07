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

    conn.commit() 
    conn.close() 


def populate_stats(): 
    """ Periodically update stats """ 
    logger.info(f"Periodic Request Process Has Started")
    
    timestamp_now = datetime.now()
    timestamp_now_str = timestamp_now.strftime("%Y-%m-%d %H:%M:%S")
    session = DB_SESSION() 
    try:
        readings = session.query(Stats).order_by(Stats.last_updated.desc()).first()

        # results = [] 

        # for reading in readings: 
        #     results.append(reading.to_dict())
        results = readings.to_dict()["last_updated"].replace(microsecond=0)
    except:
        results = {'num_of_review': 0, 'avg_age': 22.2, 'avg_rating': 4.5, 'total_sale': 1100.00, 'num_of_ticket':2, 'last_updated':'0001-01-01 01:01:01'}

    session.close()
    # print(results)
    review_url = f"{app_config['eventstore']['url']}/movie/review?start_timestamp={results['last_updated']}&end_timestamp={timestamp_now_str}"
    ticket_url = f"{app_config['eventstore']['url']}/movie/ticket?start_timestamp={results['last_updated']}&end_timestamp={timestamp_now_str}"
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
        session = DB_SESSION()
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
    default_stats = {'num_of_review': 0, 'avg_age': 22.2, 'avg_rating': 4.5, 'total_sale': 1100.00, 'num_of_ticket':2, 'last_updated':'0001-01-01 01:01:01'} 
    try:
        session = DB_SESSION() 


        results = session.query(Stats).order_by(Stats.last_updated.desc()).first() 
    
    
        session.close()
        return results.to_dict(), 200
    except:
        return default_stats, 200



def init_scheduler():
    sched = BackgroundScheduler(daemon=True) 
    sched.add_job(populate_stats,'interval',seconds=app_config['scheduler']['period_sec']) 
    sched.start()

def get_health():
    return 200

app = connexion.FlaskApp(__name__, specification_dir='')
CORS(app.app)
if "TARGET_ENV" not in os.environ or os.environ["TARGET_ENV"] != "test":
    CORS(app.app)
    app.app.config['CORS_HEADERS'] = 'Content-Type'
app.add_api(yaml_file, base_path="/processing", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    init_scheduler() 
    app.run(port=8100, use_reloader=False)
