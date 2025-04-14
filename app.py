import streamlit as st
import numpy as np
import pandas as pd
import time
import cv2
import requests
from io import BytesIO
from PIL import Image
from datetime import datetime
from ultralytics import YOLO
import paho.mqtt.publish as publish
import folium
from streamlit_folium import st_folium
import random

# Judul Aplikasi
st.markdown('<h1 style="text-align: center;">HelmAware</h1>', unsafe_allow_html=True)
st.markdown('<h2 style="text-align: center;">Smart Sensor Based Hazard Alarm System for Construction Workers</h2>', unsafe_allow_html=True)

# ---------- Toggle Feature ----------
col1, col2 = st.columns([1, 2])
with col1:
    on = st.toggle("Activate feature")

with col2:
    if on:
        st.markdown('<h6 style="text-align: left;">✅ Feature Activated</h6>', unsafe_allow_html=True)
    else:
        st.markdown('<h6 style="text-align: left;">🛑 Feature Deactivated</h6>', unsafe_allow_html=True)

# ---------- Simulasi Data Suhu & Kelembapan ----------
np.random.seed(42)
minutes = 60 * 24  # 1 hari = 1440 menit
dates = pd.date_range(start='2025-01-01', periods=minutes, freq='T')

# Suhu: 30°C ± fluktuasi sinusoidal
temp_max = 30 + 3 * np.sin(np.linspace(0, 4 * np.pi, minutes)) + np.random.normal(0, 0.5, minutes)

# Kelembapan: 60% ± fluktuasi sinusoidal
humidity = 60 + 10 * np.sin(np.linspace(0, 4 * np.pi, minutes)) + np.random.normal(0, 1.5, minutes)

# Buat DataFrame
df = pd.DataFrame({
    'date': dates,
    'temp_max': temp_max,
    'humidity': humidity
})
df.set_index('date', inplace=True)

# ---------- Temperature Chart ----------
st.markdown('<h2 style="text-align: left;">🌡️ Temperature Graph</h2>', unsafe_allow_html=True)
temp_chart_placeholder = st.empty()

# ---------- Humidity Chart ----------
st.markdown('<h2 style="text-align: left;">💧 Humidity Graph</h2>', unsafe_allow_html=True)
humidity_chart_placeholder = st.empty()

# ---------- Real-Time or Static ----------
if on:
    temp_data = []
    humidity_data = []

    for i in range(1, len(df)):
        temp_data.append(df.iloc[i - 1]['temp_max'])
        humidity_data.append(df.iloc[i - 1]['humidity'])

        # Temp chart update
        temp_chart_placeholder.line_chart(pd.DataFrame(temp_data, columns=["temp_max"]))

        # Humidity chart update
        humidity_chart_placeholder.line_chart(pd.DataFrame(humidity_data, columns=["humidity"]))

        time.sleep(0.1)  # Ganti ke 1 detik kalau mau lebih lambat
else:
    temp_chart_placeholder.line_chart(df['temp_max'])
    humidity_chart_placeholder.line_chart(df['humidity'])

# ========== KONFIGURASI UBIDOTS DAN ESP32-CAM ==========
UBIDOTS_TOKEN = "YOUR_UBIDOTS_TOKEN"
UBIDOTS_BROKER = "industrial.api.ubidots.com"
DEVICE_LABEL = "esp32-cam"
VARIABLE_LABEL = "alert"
CAMERA_SNAPSHOT_URL = "http://YOUR_ESP32_CAM_URL/capture"

# Inisialisasi session state
if "detecting" not in st.session_state:
    st.session_state.detecting = False
if "alert_active" not in st.session_state:
    st.session_state.alert_active = False
if "last_alert_time" not in st.session_state:
    st.session_state.last_alert_time = 0
if "logs" not in st.session_state:
    st.session_state.logs = []
if "motion_detected" not in st.session_state:
    st.session_state.motion_detected = False

# ========== SECTION: ESP32-CAM + YOLO + UBIDOTS ==========
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

def get_snapshot():
    try:
        response = requests.get(CAMERA_SNAPSHOT_URL, timeout=3)
        if response.status_code == 200:
            img_bytes = response.content
            img = Image.open(BytesIO(img_bytes))
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        else:
            st.warning(f"⚠ Failed to fetch snapshot: Status Code {response.status_code}")
            return None
    except Exception as e:
        st.warning(f"⚠ Failed to fetch snapshot: {e}")
        return None

# Load YOLO model
model = YOLO("yolov8n.pt")

frame_holder = st.empty()
log_holder = st.empty()

# Motion Detection Helper
def detect_motion(frame, last_frame, min_area=500):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    
    if last_frame is None:
        return gray, False
    
    delta_frame = cv2.absdiff(last_frame, gray)
    thresh = cv2.threshold(delta_frame, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    
    contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    motion_detected = False
    for contour in contours:
        if cv2.contourArea(contour) < min_area:
            continue
        motion_detected = True
        break

    return gray, motion_detected

# Start/Stop Detection Buttons
col1, col2 = st.columns(2)
with col1:
    if not st.session_state.detecting and st.button("▶ Start Detection"):
        st.session_state.detecting = True
with col2:
    if st.session_state.detecting and st.button("⏹ Stop Detection"):
        st.session_state.detecting = False
        publish_to_ubidots(0)
        st.success("Detection stopped.")

# Detection loop
last_frame = None
if st.session_state.detecting:
    frame = get_snapshot()
    if frame is not None:
        last_frame, motion_detected = detect_motion(frame, last_frame)
        
        if motion_detected != st.session_state.motion_detected:
            st.session_state.motion_detected = motion_detected
            if motion_detected:
                st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🚨 Motion Detected")
                st.toast("🚨 Motion Detected!")
            else:
                st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Motion Cleared")
                st.toast("✅ Motion Cleared")

        # Continue with YOLO detection if needed
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
                st.session_state.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🚨 {label.upper()} - Area: {int(area)}")
                break

        if not hazard_detected:
            reset_alert_if_needed()

        frame_holder.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), channels="RGB")

    if st.session_state.logs:
        log_holder.markdown("### 📝 Detection Log\n" + "\n".join(st.session_state.logs[-10:]))

import streamlit as st
import folium
from streamlit_folium import st_folium
import time

# Set the title of the app
st.title("Real-Time Interactive Map")

# Use a JavaScript snippet to get the browser's geolocation and pass it to Streamlit
st.markdown("""
    <script>
    navigator.geolocation.getCurrentPosition(function(position) {
        const lat = position.coords.latitude;
        const lon = position.coords.longitude;
        window.parent.postMessage({lat: lat, lon: lon}, "*");
    });
    </script>
""", unsafe_allow_html=True)

# Set up placeholder for the map
map_placeholder = st.empty()

# Function to create a real-time map
def create_map(lat, lon):
    # Create map centered on the given lat, lon
    m = folium.Map(location=[lat, lon], zoom_start=12)
    marker = folium.Marker([lat, lon], popup="Current Location")
    marker.add_to(m)
    return m

# Simulating real-time location (you will replace this part with actual real-time data fetching)
lat, lon = 37.7749, -122.4194  # Example: San Francisco

# Create and display the initial map with the real-time location
m = create_map(lat, lon)
map_placeholder = st_folium(m, width=725)

# Update the map continuously with real-time data
# This part simulates location updates (you can replace with actual updates)
for _ in range(10):  # Simulate 10 updates (you can adjust the number)
    time.sleep(3)
    # In a real implementation, you would fetch new lat, lon from geolocation API here
    lat += 0.0001  # Simulate slight movement
    lon += 0.0001
    m = create_map(lat, lon)
    map_placeholder = st_folium(m, width=725)

