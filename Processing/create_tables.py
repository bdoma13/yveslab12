import sqlite3 
 
conn = sqlite3.connect('stats.sqlite') 
 
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