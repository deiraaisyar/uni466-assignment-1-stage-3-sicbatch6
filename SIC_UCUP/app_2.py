import streamlit as st
import pandas as pd
import numpy as np
import cv2
from ultralytics import YOLO
from PIL import Image
import paho.mqtt.publish as publish
from datetime import datetime
import requests
from io import BytesIO
import time

# === CONFIG ===
CAMERA_SNAPSHOT_URL = "http://192.168.0.115:81/stream"
UBIDOTS_TOKEN = "BBUS-8rMLXoEFppMoI2rt7r9zFIOEu53CTe"
UBIDOTS_BROKER = "industrial.api.ubidots.com"
DEVICE_LABEL = "esp32-sic6-stage3"
VARIABLE_LABEL = "alert"

# === GLOBAL STATES ===
if "logs" not in st.session_state:
    st.session_state.logs = []
if "last_alert_time" not in st.session_state:
    st.session_state.last_alert_time = 0
if "alert_active" not in st.session_state:
    st.session_state.alert_active = False
if "detecting" not in st.session_state:
    st.session_state.detecting = False

# === APP LAYOUT ===
st.set_page_config(page_title="Warga Naget's Portfolio", layout="wide")
st.title("👤 Warga Naget's Portfolio Website")
st.write("Welcome to my portfolio website 🚀")

# === SECTION: ABOUT ME ===
with st.container():
    st.subheader("🧑‍💻 About Me")
    st.write("I’m Warga Naget — an enthusiastic developer exploring embedded vision, AI, and IoT.")
    chart_data = pd.DataFrame(np.random.randn(20, 3), columns=["a", "b", "c"])
    st.area_chart(chart_data)

# === SECTION: CHATBOX ===
prompt = st.chat_input("Say something")
if prompt:
    st.write(f"💬 You said: {prompt}")


# === SECTION: ESP32-CAM + YOLO + UBIDOTS ===
st.header("🚨 ESP32-CAM Object Proximity Detection")

# Sidebar controls
confidence_thresh = st.sidebar.slider("Confidence Threshold", 0.1, 1.0, 0.5)
area_thresh = st.sidebar.slider("Bounding Box Area Threshold", 10000, 150000, 50000)
reset_delay = st.sidebar.slider("Reset delay (seconds)", 2, 10, 4)

if st.sidebar.button("🔔 Manually Trigger Alert"):
    topic = f"/v1.6/devices/{DEVICE_LABEL}/{VARIABLE_LABEL}"
    payload = "{\"value\":1}"
    publish.single(topic, payload, hostname=UBIDOTS_BROKER, port=1883,
                   auth={'username': UBIDOTS_TOKEN, 'password': ''})
    st.sidebar.success("Alert sent manually!")

# Helper functions
def publish_to_ubidots(value):
    topic = f"/v1.6/devices/{DEVICE_LABEL}/{VARIABLE_LABEL}"
    payload = f"{{\"value\":{value}}}"
    publish.single(topic, payload, hostname=UBIDOTS_BROKER, port=1883,
                   auth={'username': UBIDOTS_TOKEN, 'password': ''})

def trigger_alert():
    if not st.session_state.alert_active:
        publish_to_ubidots(1)
        st.session_state.alert_active = True
        st.toast("🚨 ALERT: Object Too Close!")
    st.session_state.last_alert_time = time.time()

def reset_alert_if_needed():
    if st.session_state.alert_active and (time.time() - st.session_state.last_alert_time > reset_delay):
        publish_to_ubidots(0)
        st.session_state.alert_active = False
        st.toast("✅ Cleared alert")

# Replace get_snapshot() with this
def get_frame_from_stream(url):
    cap = cv2.VideoCapture(url)
    ret, frame = cap.read()
    cap.release()
    if ret:
        return frame
    else:
        st.warning("⚠️ Failed to grab frame from stream.")
        return None


# Load YOLO model
model = YOLO("yolov8n.pt")

frame_holder = st.empty()
log_holder = st.empty()

# Start/Stop Detection Buttons
col1, col2 = st.columns(2)
with col1:
    if not st.session_state.detecting and st.button("▶️ Start Detection"):
        st.session_state.detecting = True
with col2:
    if st.session_state.detecting and st.button("⏹️ Stop Detection"):
        st.session_state.detecting = False
        publish_to_ubidots(0)  # Ensure buzzer is reset
        st.success("Detection stopped.")

# Detection loop using continuous stream
if st.session_state.detecting:
    cap = cv2.VideoCapture(CAMERA_SNAPSHOT_URL)

    if not cap.isOpened():
        st.error("❌ Failed to open ESP32-CAM stream.")
        st.session_state.detecting = False
    else:
        while st.session_state.detecting:
            ret, frame = cap.read()
            if not ret or frame is None:
                st.warning("⚠️ Failed to read frame.")
                break

            results = model(frame)[0]
            annotated = results.plot()
            hazard_detected = False

            for box in results.boxes:
                cls = int(box.cls[0])
                label = model.names[cls]
                x1, y1, x2, y2 = box.xyxy[0]
                area = (x2 - x1) * (y2 - y1)

                if label == "person":
                    if area > area_thresh:
                        hazard_detected = True
                        trigger_alert()
                        st.session_state.logs.append(
                            f"[{datetime.now().strftime('%H:%M:%S')}] 🚨 {label.upper()} - Area: {int(area)}"
                        )
                    else:
                        # Person is present, but too far
                        st.session_state.logs.append(
                            f"[{datetime.now().strftime('%H:%M:%S')}] ℹ️ {label.upper()} detected - Area: {int(area)} (too small)"
                        )
                    break  # Exit after first person detection

            # Reset if no hazard condition met
            if not hazard_detected:
                reset_alert_if_needed()


            frame_holder.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), channels="RGB")

            # break loop if user presses stop or app re-runs
            if not st.runtime.exists():
                break

        cap.release()
