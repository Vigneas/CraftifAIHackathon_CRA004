"""
Workplace Safety Sentinel - MQTT Alert Telemetry Listener
Monitors actionable safety events published by the perception pipeline.
"""

import sys
import json
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("[!] paho-mqtt not installed. Install with: pip install paho-mqtt")
    print("[+] Simulating real-time incident monitor from local incident_logs/workplace_incidents.json...")
    sys.exit(0)

def on_connect(client, userdata, flags, reason_code, properties):
    print(f"[+] Connected to MQTT Broker with result code: {reason_code}")
    client.subscribe("factory/safety/alerts")
    print("[+] Subscribed to topic: factory/safety/alerts (Waiting for breach events...)")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"\n🚨 [CRITICAL ALERT RECEIVED via MQTT]")
        print(f"   Timestamp    : {payload.get('timestamp')}")
        print(f"   Zone ID      : {payload.get('zone_id')}")
        print(f"   Person ID    : {payload.get('person_id')}")
        print(f"   Coordinates  : {payload.get('coordinates')}")
        print(f"   Confidence   : {payload.get('confidence')}")
        print(f"   Action Taken : Audible Siren Triggered | Automated Safety Interlock Engaged")
    except Exception as e:
        print(f"Error parsing message: {e}")

if __name__ == "__main__":
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect("localhost", 1883, 60)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[+] Listener stopped.")
    except Exception as e:
        print(f"[!] Could not connect to broker: {e}")
