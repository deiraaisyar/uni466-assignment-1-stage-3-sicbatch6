import streamlit as st
import cv2
import numpy as np
from ultralytics import YOLO
from PIL import Image
import paho.mqtt.publish as publish
from datetime import datetime
import requests
from io import BytesIO
import time

# === CONFIG ===
CAMERA_SNAPSHOT_URL = "http://192.168.1.229/capture"
UBIDOTS_TOKEN = "BBUS-iYTamlBTLRQ8di2mUMohiW4ErEmBGf"
UBIDOTS_BROKER = "industrial.api.ubidots.com"
DEVICE_LABEL = "hazard-node"
VARIABLE_LABEL = "alert"

# === STREAMLIT UI ===
st.set_page_config(page_title="ESP32-CAM Hazard Detector", layout="wide")
st.title("📸 ESP32-CAM Object Proximity Alert")

confidence_thresh = st.sidebar.slider("Confidence Threshold", 0.1, 1.0, 0.5)
area_thresh = st.sidebar.slider("Bounding Box Area Threshold", 10000, 150000, 50000)
reset_delay = st.sidebar.slider("Reset delay (seconds)", 2, 10, 4)

# Manual Trigger Button
if st.sidebar.button("🔔 Manually Trigger Alert"):
    topic = f"/v1.6/devices/{DEVICE_LABEL}/{VARIABLE_LABEL}"
    payload = "{\"value\":1}"
    publish.single(topic, payload, hostname=UBIDOTS_BROKER, port=1883,
                   auth={'username': UBIDOTS_TOKEN, 'password': ''})
    st.sidebar.success("Alert sent manually!")

# Load YOLOv8
model = YOLO("yolov8n.pt")

frame_holder = st.empty()
log_holder = st.empty()
logs = []

last_alert_time = 0
alert_active = False

def publish_to_ubidots(value):
    topic = f"/v1.6/devices/{DEVICE_LABEL}/{VARIABLE_LABEL}"
    payload = f"{{\"value\":{value}}}"
    publish.single(topic, payload, hostname=UBIDOTS_BROKER, port=1883,
                   auth={'username': UBIDOTS_TOKEN, 'password': ''})

def trigger_alert():
    global alert_active, last_alert_time
    if not alert_active:
        publish_to_ubidots(1)
        alert_active = True
        st.toast("🚨 ALERT: Object Too Close!")
    last_alert_time = time.time()

def reset_alert_if_needed():
    global alert_active
    if alert_active and (time.time() - last_alert_time > reset_delay):
        publish_to_ubidots(0)
        alert_active = False
        st.toast("✅ Cleared alert")

def get_snapshot():
    try:
        response = requests.get(CAMERA_SNAPSHOT_URL, timeout=3)
        img_bytes = response.content
        img = Image.open(BytesIO(img_bytes))
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        st.warning(f"⚠️ Failed to fetch snapshot: {e}")
        return None

# Main loop
while True:
    frame = get_snapshot()
    if frame is None:
        continue

    results = model(frame)[0]
    annotated = results.plot()
    hazard_detected = False

    for box in results.boxes:
        cls = int(box.cls[0])
        label = model.names[cls]
        x1, y1, x2, y2 = box.xyxy[0]
        area = (x2 - x1) * (y2 - y1)

        if label == "person" and area > area_thresh:
            hazard_detected = True
            trigger_alert()
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🚨 {label.upper()} - Area: {int(area)}")
            break

    if not hazard_detected:
        reset_alert_if_needed()

    frame_holder.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), channels="RGB")
    
    if logs:
        log_holder.markdown("### 🚨 Detection Log\n" + "\n".join(logs[-10:]))

    if not st.runtime.exists():
        break
