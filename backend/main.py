import sqlite3
import json
import threading
import paho.mqtt.client as mqtt
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import contextmanager

DB_PATH = "data/waste.db"
MQTT_HOST = "mosquitto"  # numele serviciului din docker-compose
MQTT_PORT = 1883 # portul standard MQTT

#------------SQL SETUP------------#

def initialize_database():
    conn = sqlite3.connect(DB_PATH) # conectează la baza de date (sau o creează dacă nu există)
    conn.execute('''CREATE TABLE IF NOT EXISTS measurements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        container_id TEXT NOT NULL,
                        ts TEXT,
                        fill_pct REAL,
                        temp_c REAL,
                        tilt INTEGER,
                        battery_pct REAL,
                        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )''') # creează tabelul measurements dacă nu există deja
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # permite accesarea coloanelor prin nume în loc de index
    try:
        yield conn # yield conn # yield permite utilizarea context managerului cu "with"
    finally:
        conn.close() # închide conexiunea la baza de date


#------------MQTT SETUP------------#

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe("waste/+/telemetry")  # se abonează la toate topicurile de tip waste/+/telemetry

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode()) # transofrmă payload-ul în dicționar Python
        container_id = msg.topic.split('/')[1] # extrage container_id din topic

        with get_db() as conn:
            conn.execute(''' INSERT INTO measurements (container_id, ts, fill_pct, temp_c, tilt, battery_pct) VALUES (?, ?, ?, ?, ?, ?)''',
                         (container_id, data.get('ts'), data.get('fill_pct'), data.get('temp_c'), data.get('tilt'), data.get('battery_pct'))) 
            conn.commit() # salvează modificările în baza de date
            print(f"Inserted data for container {container_id} into database.")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Mesaj invalid pe {msg.topic}: {e}")

def start_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_forever()  # blocant - de-asta rulează pe thread separat
                         
#------------FASTAPI SETUP------------#

app = FastAPI() # creează aplicația FastAPI
app.add_middleware(CORSMiddleware, allow_origins=["*"]) # permite cereri de la orice origine (pentru dezvoltare)

@app.on_event("startup") # eveniment care se declanșează la pornirea aplicației
def startup():
    initialize_database()
    thread = threading.Thread(target=start_mqtt, daemon=True) # rulează funcția start_mqtt pe un thread separat, astfel încât să nu blocheze serverul FastAPI
    thread.start() # pornește thread-ul

@app.get("/containers") # ruta GET pentru a obține lista de containere cu ultima măsurătoare
def get_containers():
    """Ultima măsurătoare pentru fiecare container."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT container_id, ts, fill_pct, temp_c, tilt, battery_pct, received_at
            FROM measurements m1
            WHERE received_at = (
                SELECT MAX(received_at) FROM measurements m2
                WHERE m2.container_id = m1.container_id
            )
        """).fetchall()
        return [dict(r) for r in rows] # returnează lista de containere cu ultima măsurătoare

@app.get("/containers/{container_id}/history") # ruta GET pentru a obține istoricul măsurătorilor unui container
def get_history(container_id: str, limit: int = 50):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM measurements WHERE container_id = ?
               ORDER BY received_at DESC LIMIT ?""",
            (container_id, limit)
        ).fetchall()
        return [dict(r) for r in rows] # returnează istoricul măsurătorilor pentru containerul specificat