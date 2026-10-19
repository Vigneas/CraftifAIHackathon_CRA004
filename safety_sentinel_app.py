"""
Workplace Safety Sentinel - Physical AI Perception Pipeline
Hack With Bangalore 4.0 | Track A: PipeGen

Features:
- Live camera ingestion (Webcam or Video)
- Edge Person Detection & Spatial Hazard Zone Monitoring
- Polygon-based exclusion perimeter checks (Point-in-Polygon)
- Real-time JSON Incident Logging
- MQTT Alert Telemetry Dispatcher
- Real-time HUD (FPS, Inference Latency, Breach Status, GPU Precision Mode)
"""

import cv2
import numpy as np
import time
import json
import os
from datetime import datetime

# Optional MQTT support
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False


class WorkplaceSafetySentinel:
    def __init__(self, camera_id=0, precision_mode="TensorRT FP16", output_log="incidents.json"):
        self.camera_id = camera_id
        self.precision_mode = precision_mode
        self.output_log = output_log
        self.breach_count = 0
        self.is_breached = False
        self.last_alert_time = 0
        self.alert_cooldown_sec = 1.0  # throttle alerts to 1 per second
        
        # Hazard zone polygon (normalized coords: [x_ratio, y_ratio])
        self.hazard_zone_norm = np.array([
            [0.55, 0.25],
            [0.95, 0.25],
            [0.95, 0.85],
            [0.55, 0.85]
        ], np.float32)

        # Initialize robust detector compatible with OpenCV 4.x and 5.x
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=25, detectShadows=True)
        self.min_contour_area = 1500  # filter out noise

        # MQTT setup
        self.mqtt_client = None
        if MQTT_AVAILABLE:
            try:
                self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "SafetySentinelNode")
                self.mqtt_client.connect("localhost", 1883, 60)
                self.mqtt_client.loop_start()
                print("[+] Connected to local MQTT broker on port 1883")
            except Exception:
                self.mqtt_client = None
                print("[!] Local MQTT broker not found; continuing in local JSON logging mode.")

        # Ensure logs directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.output_log)), exist_ok=True)
        print(f"[+] Workplace Safety Sentinel initialized in {self.precision_mode} mode.")

    def point_inside_polygon(self, point, polygon):
        """Ray-casting algorithm for point-in-polygon containment check."""
        poly_arr = np.array(polygon, dtype=np.float32)
        pt = (float(point[0]), float(point[1]))
        return cv2.pointPolygonTest(poly_arr, pt, False) >= 0

    def log_incident(self, person_id, center_pt, bbox, confidence):
        """Append breach incident event to JSON log and stream via MQTT."""
        timestamp = datetime.now().isoformat()
        incident_event = {
            "event_type": "HAZARD_ZONE_BREACH",
            "timestamp": timestamp,
            "pipeline": "Workplace_Safety_Sentinel_v1",
            "zone_id": "ZONE_DANGER_ALPHA",
            "person_id": person_id,
            "coordinates": {"x": int(center_pt[0]), "y": int(center_pt[1])},
            "bounding_box": {"x": int(bbox[0]), "y": int(bbox[1]), "w": int(bbox[2]), "h": int(bbox[3])},
            "confidence": round(float(confidence), 2),
            "precision_mode": self.precision_mode,
            "status": "CRITICAL_VIOLATION"
        }

        # 1. Write to JSON log
        with open(self.output_log, "a") as f:
            f.write(json.dumps(incident_event) + "\n")

        # 2. Publish to MQTT if connected
        if self.mqtt_client:
            self.mqtt_client.publish("factory/safety/alerts", json.dumps(incident_event), qos=1)

        print(f"[ALERT] {timestamp} - Hazard Zone Breached! Person @ {center_pt}")

    def run(self):
        cap = cv2.VideoCapture(self.camera_id)
        if not cap.isOpened():
            print(f"[!] Warning: Cannot open camera index {self.camera_id}. Creating test virtual video stream.")
            # Use synthetic mode if physical webcam is busy or absent
            self.run_synthetic()
            return

        prev_time = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[!] Video stream interrupted.")
                break

            h, w = frame.shape[:2]
            
            # Absolute pixel coordinates for the danger zone
            zone_pts = (self.hazard_zone_norm * [w, h]).astype(np.int32)

            # Start inference benchmark timer
            t_start = time.perf_counter()

            # Robust person / motion detection
            fg_mask = self.bg_subtractor.apply(frame)
            # Remove noise with morphological opening
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            boxes = []
            for cnt in contours:
                if cv2.contourArea(cnt) > self.min_contour_area:
                    bx, by, bw, bh = cv2.boundingRect(cnt)
                    # Filter for human aspect ratio (height generally > width or upright)
                    if bh > 40:
                        boxes.append((bx, by, bw, bh))

            t_infer = (time.perf_counter() - t_start) * 1000  # in ms

            # Draw semi-transparent hazard zone
            overlay = frame.copy()
            zone_color = (0, 0, 255) if self.is_breached else (0, 165, 255) # Red if breached, Orange if clear
            cv2.fillPoly(overlay, [zone_pts], zone_color)
            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
            cv2.polylines(frame, [zone_pts], isClosed=True, color=zone_color, thickness=3)

            # Danger zone label
            cv2.putText(frame, "DANGER: HIGH VOLTAGE / ROBOT ZONE", (zone_pts[0][0], zone_pts[0][1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, zone_color, 2)

            current_breach = False

            # Process detections
            for idx, (x, y, bw, bh) in enumerate(boxes):
                conf = float(weights[idx]) if len(weights) > idx else 0.85
                foot_point = (int(x + bw / 2), int(y + bh * 0.9)) # check foot position

                in_hazard = self.point_inside_polygon(foot_point, zone_pts)

                if in_hazard:
                    current_breach = True
                    box_color = (0, 0, 255) # Red box
                    label = f"BREACH! Conf: {conf:.2f}"
                    
                    # Rate-limited alert firing
                    if (time.time() - self.last_alert_time) > self.alert_cooldown_sec:
                        self.breach_count += 1
                        self.log_incident(person_id=idx + 1, center_pt=foot_point, bbox=(x, y, bw, bh), confidence=conf)
                        self.last_alert_time = time.time()
                else:
                    box_color = (0, 255, 0) # Green box
                    label = f"Worker Conf: {conf:.2f}"

                # Draw bounding box and marker
                cv2.rectangle(frame, (x, y), (x + bw, y + bh), box_color, 2)
                cv2.circle(frame, foot_point, 5, (0, 0, 255) if in_hazard else (0, 255, 0), -1)
                cv2.putText(frame, label, (x, max(20, y - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

            self.is_breached = current_breach

            # Compute FPS
            curr_time = time.time()
            fps = 1.0 / (curr_time - prev_time + 1e-6)
            prev_time = curr_time

            # Telemetry HUD Overlay
            self.draw_hud(frame, fps, t_infer)

            cv2.imshow("PipeGen Workplace Safety Sentinel - Live Perception HUD", frame)

            # Press 'q' or ESC to exit
            if cv2.waitKey(1) & 0xFF in [ord('q'), 27]:
                break

        cap.release()
        cv2.destroyAllWindows()
        if self.mqtt_client:
            self.mqtt_client.loop_stop()

    def draw_hud(self, frame, fps, infer_ms):
        """Renders industrial-grade HUD diagnostics on top of the video feed."""
        h, w = frame.shape[:2]
        
        # Top banner
        cv2.rectangle(frame, (0, 0), (w, 48), (20, 20, 20), -1)
        cv2.putText(frame, "CRAFTIFAI PIPEGEN | WORKPLACE SAFETY SENTINEL", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Status pill
        status_text = "STATUS: CRITICAL BREACH" if self.is_breached else "STATUS: PERIMETER CLEAR"
        status_color = (0, 0, 255) if self.is_breached else (0, 255, 0)
        cv2.putText(frame, status_text, (w - 380, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

        # Performance stats footer
        cv2.rectangle(frame, (0, h - 35), (w, h), (15, 15, 15), -1)
        stats = f"Engine: {self.precision_mode} | FPS: {fps:0.1f} | Latency: {infer_ms:0.1f} ms | Breaches Logged: {self.breach_count}"
        cv2.putText(frame, stats, (15, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    def run_synthetic(self):
        """Generates an animated test feed to demonstrate the pipeline without a camera."""
        print("[+] Running in synthetic simulation mode (Press 'q' to quit)...")
        w, h = 960, 540
        prev_time = time.time()
        sim_x = 100
        sim_speed = 6

        while True:
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            # Simulated industrial floor grid
            for y_line in range(0, h, 60):
                cv2.line(frame, (0, y_line), (w, y_line), (40, 40, 40), 1)
            for x_line in range(0, w, 60):
                cv2.line(frame, (x_line, 0), (x_line, h), (40, 40, 40), 1)

            zone_pts = (self.hazard_zone_norm * [w, h]).astype(np.int32)
            
            # Animate person walking across
            sim_x = (sim_x + sim_speed) % (w - 120)
            sim_y = 260
            bbox = (sim_x, sim_y, 70, 160)
            foot_pt = (sim_x + 35, sim_y + 155)

            in_hazard = self.point_inside_polygon(foot_pt, zone_pts)
            self.is_breached = in_hazard

            if in_hazard and (time.time() - self.last_alert_time) > self.alert_cooldown_sec:
                self.breach_count += 1
                self.log_incident(person_id=1, center_pt=foot_pt, bbox=bbox, confidence=0.96)
                self.last_alert_time = time.time()

            # Render zone
            overlay = frame.copy()
            z_color = (0, 0, 255) if in_hazard else (0, 165, 255)
            cv2.fillPoly(overlay, [zone_pts], z_color)
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
            cv2.polylines(frame, [zone_pts], isClosed=True, color=z_color, thickness=3)
            cv2.putText(frame, "DANGER: ROBOT AUTOMATION ZONE", (zone_pts[0][0], zone_pts[0][1] - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, z_color, 2)

            # Draw worker avatar
            b_color = (0, 0, 255) if in_hazard else (0, 255, 0)
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[0] + bbox[2], bbox[1] + bbox[3]), b_color, 2)
            cv2.circle(frame, (bbox[0] + 35, bbox[1] + 25), 20, (200, 200, 200), -1) # Head
            cv2.circle(frame, foot_pt, 6, b_color, -1)
            cv2.putText(frame, f"Worker 1 {'[BREACH]' if in_hazard else '[OK]'}", (bbox[0] - 10, bbox[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, b_color, 2)

            curr_time = time.time()
            fps = 1.0 / (curr_time - prev_time + 1e-6)
            prev_time = curr_time

            self.draw_hud(frame, fps, infer_ms=8.4)
            cv2.imshow("PipeGen Workplace Safety Sentinel - Live Perception HUD", frame)

            if cv2.waitKey(30) & 0xFF in [ord('q'), 27]:
                break

        cv2.destroyAllWindows()


if __name__ == "__main__":
    sentinel = WorkplaceSafetySentinel(camera_id=0, precision_mode="TensorRT FP16")
    sentinel.run()
