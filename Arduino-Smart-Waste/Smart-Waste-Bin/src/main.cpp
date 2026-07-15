#include <WiFiS3.h>
#include <PubSubClient.h>
#include <DHT.h>

#define DHT_PIN 2
#define DHT_TYPE DHT11

#define TRIG_PIN 4
#define ECHO_PIN 3

// inaltimea reala, in cm, de la senzor pana la fundul containerului (gol)
// MASURATI-O MANUAL, cu rigla, si actualizati valoarea aici
#define CONTAINER_HEIGHT_CM 14

const char* ssid = "i steal data";
const char* password = "muiesteaua";

const char* mqttBroker = "10.201.186.142";  // IP-ul real al laptopului cu Docker
const int mqttPort = 1883;

DHT dht(DHT_PIN, DHT_TYPE);

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

unsigned long lastPublish = 0;
const unsigned long PUBLISH_INTERVAL = 30000;  // 30 secunde, ca la simulator.py

void connectWiFi() {
  Serial.print("Conectare la WiFi");

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi conectat");
  Serial.print("IP Arduino: ");
  Serial.println(WiFi.localIP());
}

void connectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Conectare la MQTT...");

    if (mqttClient.connect("arduino-r4")) {
      Serial.println("conectat");
    } else {
      Serial.print("eroare: ");
      Serial.println(mqttClient.state());

      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(9600);

  dht.begin();

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  connectWiFi();

  mqttClient.setServer(mqttBroker, mqttPort);
}

void loop() {
  // reconectare doar daca s-a pierdut conexiunea - nu blocheaza restul codului
  if (!mqttClient.connected()) {
    connectMQTT();
  }

  // trebuie apelat cat mai des posibil, ca sa mentina conexiunea MQTT vie
  mqttClient.loop();

  unsigned long now = millis();

  // publicam doar daca au trecut 30 de secunde de la ultima publicare
  if (now - lastPublish >= PUBLISH_INTERVAL) {
    lastPublish = now;

    float temperatura = dht.readTemperature();

    // trimitem un puls ultrasonic si masuram cat dureaza ecoul
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);

    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);

    digitalWrite(TRIG_PIN, LOW);

    long durata = pulseIn(ECHO_PIN, HIGH, 30000);  // timeout 30ms, evita blocare la citire lipsa

    if (durata == 0) {
      // senzorul nu a detectat nimic (prea departe, sau eroare hardware)
      // sarim peste aceasta citire, incercam din nou la urmatorul ciclu
      Serial.println("Eroare citire senzor ultrasonic - masuratoare ignorata");
      return;
    }

    float distanta = durata * 0.0343 / 2;  // conversie in cm (viteza sunetului / 2, dus-intors)

    // transformam distanta (cm pana la gunoi) in procent de umplere
    // senzor sus, distanta mica = plin; distanta mare = gol
    float fill_pct = ((CONTAINER_HEIGHT_CM - distanta) / CONTAINER_HEIGHT_CM) * 100.0;
    fill_pct = constrain(fill_pct, 0, 100);  // limitam intre 0 si 100, evitam valori aberante

    char payload[128];
    snprintf(payload, sizeof(payload),
      "{\"container_id\":\"C01\",\"fill_pct\":%.1f,\"temp_c\":%.1f,\"tilt\":false}",
      fill_pct, temperatura);

    mqttClient.publish("waste/C01/telemetry", payload);

    Serial.println("Date publicate:");
    Serial.println(payload);
    Serial.print("Distanta bruta masurata (cm): ");
    Serial.println(distanta);
  }
}
