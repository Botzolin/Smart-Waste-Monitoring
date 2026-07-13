import json
import time
import random
import paho.mqtt.client as mqtt

# --- conectare MQTT ---
client = mqtt.Client()
client.connect("mosquitto", 1883, 60)
client.loop_start()

# --- citire config ---
def load_containers():
    with open("dashboard/containers.json") as f:
        return json.load(f)

# --- generare date fake-readings ---
fill_levels = {}
def next_reading(container_id):
    current = fill_levels.get(container_id, random.uniform(0, 30))  # start random la prima rulare
    current += random.uniform(0.3, 2.0)  # crestere naturala

    if current > 100:
        current = random.uniform(0, 10)  # simuleaza o colectare (golire)

    fill_levels[container_id] = current  # salvam pentru urmatoarea iteratie

    return {
        "container_id": container_id,
        "fill_pct": round(current, 1),
        "temp_c": round(random.uniform(18, 27), 1),
        "tilt": False
    }

# --- trimitere pe MQTT ---
def publish_reading(container_id):
    data = next_reading(container_id)
    topic = f"waste/{container_id}/telemetry"
    client.publish(topic, json.dumps(data))
    print(f"{container_id}: {data}")

# --- bucla principala ---
def run():
    containers = load_containers()
    while True:
        for container_id in containers:
            if container_id == "C01":
                continue
            publish_reading(container_id)
        time.sleep(30)

run()