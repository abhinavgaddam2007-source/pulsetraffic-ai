import json
import time
import paho.mqtt.client as mqtt

class MQTTController:
    def __init__(self, broker: str = "broker.hivemq.com", port: int = 1883):
        self.client = mqtt.Client(client_id="PulseTraffic_Backend_Master")
        self.broker = broker
        self.port = port

    def connect(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            print(f"[MQTT] Connected to broker {self.broker}:{self.port}")
        except Exception as e:
            print(f"[MQTT Error] Connection failed: {e}")

    def send_signal_state(self, junction_id: str, active_green_lane: str, duration_sec: int, emergency: bool = False):
        payload = {
            "junction_id": junction_id,
            "green_lane": active_green_lane,
            "duration": duration_sec,
            "emergency_override": emergency,
            "timestamp": time.time_ns() // 1_000_000  # Millisecond epoch timestamp
        }
        topic = f"pulsetraffic/signals/{junction_id}/command"
        
        # Publish with QoS=1 for ultra-fast guaranteed execution (<50ms)
        self.client.publish(topic, json.dumps(payload), qos=1)
        print(f"[MQTT Published -> {topic}] Payload: {payload}")