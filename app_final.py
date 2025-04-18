import streamlit as st
import pandas as pd
import requests
import cv2
from datetime import datetime
from paho.mqtt import publish
from ultralytics import YOLO
import time
from PIL import Image

img = Image.open('HelmAware_Header.jpg')
st.image(img)

# === CONFIG ===
# CAMERA_SNAPSHOT_URL = "http://172.20.10.2:81/stream" this for using ESP32 Camera
CAMERA_SNAPSHOT_URL = 0 # Use 0 for webcam
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

# === HELPER FUNCTIONS ===
def publish_to_ubidots(value):
    topic = f"/v1.6/devices/{DEVICE_LABEL}/{VARIABLE_LABEL}"
    payload = f"{{\"value\":{value}}}"
    publish.single(topic, payload, hostname=UBIDOTS_BROKER, port=1883,
                   auth={'username': UBIDOTS_TOKEN, 'password': ''})

# === SETUP ===
UBIDOTS_TOKEN = "BBUS-8rMLXoEFppMoI2rt7r9zFIOEu53CTe"
DEVICE_LABEL = "esp32-sic6-stage3"
headers = {"X-Auth-Token": UBIDOTS_TOKEN}

def get_ubidots_variable_value(var_label):
    url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}/{var_label}/lv"
    try:
        response = requests.get(url, headers=headers)
        print(response.status_code, response.text)  # Log response
        if response.status_code == 200:
            return float(response.text)
        else:
            return None
    except Exception as e:
        print("Error:", e)
        return None

import datetime

def get_ubidots_variable_history(var_label, limit=20):
    end_time = int(datetime.datetime.now().timestamp() * 1000)  # Waktu saat ini dalam milidetik
    start_time = int((datetime.datetime.now() - datetime.timedelta(days=1)).timestamp() * 1000)  # 24 jam lalu
    
    url = f"https://industrial.api.ubidots.com/api/v1.6/devices/{DEVICE_LABEL}/{var_label}/values?start={start_time}&end={end_time}&limit={limit}"
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            raw = response.json().get('results', [])
            data = []
            for item in raw:
                ts = pd.to_datetime(item['timestamp'], unit='ms', utc=True).tz_convert('Asia/Jakarta')
                val = item['value']
                data.append((ts, val))
            df = pd.DataFrame(data, columns=["timestamp", var_label])
            df = df.set_index("timestamp").sort_index()
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        print("Error:", e)
        return pd.DataFrame()


# === JUDUL APLIKASI ===
st.markdown('<h1 style="text-align: center;">HelmAware</h1>', unsafe_allow_html=True)
st.markdown('<h2 style="text-align: center;">Smart Sensor Based Hazard Alarm System for Construction Workers</h2>', unsafe_allow_html=True)

# === STATUS BOX ===
col1, col2, col3 = st.columns(3)

with col1:
    temp = get_ubidots_variable_value("temperature")
    st.metric(label="🌡️ Temperature", value=f"{temp:.1f} °C" if temp else "N/A")

with col2:
    hum = get_ubidots_variable_value("humidity")
    st.metric(label="💧 Humidity", value=f"{hum:.1f} %" if hum else "N/A")

with col3:
    motion = get_ubidots_variable_value("motion")
    status = "Detected" if motion == 1 else "None"
    st.metric(label="🚶 Motion", value=status)
    
# === CHARTS WITH TIME ===
st.markdown('<h2 style="text-align: left;">🌡️ Temperature Graph (Ubidots)</h2>', unsafe_allow_html=True)
temp_df = get_ubidots_variable_history("temperature")

st.write("📊 Data suhu (temperature):")
st.dataframe(temp_df)
if not temp_df.empty:
    st.line_chart(temp_df)
else:
    st.warning("⚠️ Data grafik suhu tidak tersedia.")

st.markdown('<h2 style="text-align: left;">💧 Humidity Graph (Ubidots)</h2>', unsafe_allow_html=True)
hum_df = get_ubidots_variable_history("humidity")

st.write("📊 Data kelembapan (humidity):")
st.dataframe(hum_df)
if not hum_df.empty:
    st.line_chart(hum_df)
else:
    st.warning("⚠️ Data grafik kelembapan tidak tersedia.")

# === MOTION STATUS ===
st.markdown('<h2 style="text-align: left;">🚶 Motion Sensor Status</h2>', unsafe_allow_html=True)
motion_placeholder = st.empty()

if motion is None:
    motion_placeholder.warning("⚠️ Tidak dapat mengambil data dari sensor gerak.")
elif motion == 1:
    motion_placeholder.error("🚨 GERAKAN TERDETEKSI! Harap periksa area sekitarmu!")
else:
    motion_placeholder.success("✅ Tidak ada gerakan yang terdeteksi saat ini.")

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
                            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] 🚨 {label.upper()} - Area: {int(area)}"
                        )
                    else:
                        # Person is present, but too far
                        st.session_state.logs.append(
                            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ℹ️ {label.upper()} detected - Area: {int(area)} (too small)"
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

        

        
# === CHATBOX ===
# Ambil data sensor
temp = get_ubidots_variable_value("temperature")
hum = get_ubidots_variable_value("humidity")
alert = get_ubidots_variable_value("alert")

# === KONFIGURASI GEMINI ===
GEMINI_API_KEY = 'AIzaSyAqBof9P4D2d85k3YtopLOI_k3kJdYybvw'
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-002:generateContent?key={GEMINI_API_KEY}"

def get_gemini_response(prompt, temp, hum, alert):
    GEMINI_API_KEY = 'AIzaSyAqBof9P4D2d85k3YtopLOI_k3kJdYybvw'
    GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-002:generateContent?key={GEMINI_API_KEY}"

    # Data sensor sebagai konteks
    sensor_info = f"""
    Berikut adalah data sensor terbaru dari helm cerdas:
    - Suhu: {temp:.1f}°C
    - Kelembapan: {hum:.1f}%
    - Status Bahaya: {'Bahaya terdeteksi' if alert == 1 else 'Tidak ada bahaya terdeteksi'}
    """

    # Prompt akhir untuk dikirim ke Gemini
    full_prompt = f"""
    Anda adalah asisten keselamatan dari sistem helm cerdas di dalam proyek konstruksi. Jawablah pertanyaan pengguna berdasarkan informasi ini:
    {sensor_info}

    Pertanyaan pengguna: {prompt}
    """

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [
            {
                "parts": [{"text": full_prompt}]
            }
        ]
    }

    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            return f"⚠️ Error dari Gemini API. Status: {response.status_code}\n{response.text}"
    except Exception as e:
        return f"⚠️ Terjadi error: {str(e)}"

# === INTERFACE CHAT ===
st.title("🛠️ HelmAware Chat Bot")

prompt = st.chat_input("💬 Tanyakan sesuatu tentang kondisi sensor atau keselamatan...")

if prompt:
    st.chat_message("user").write(prompt)
    prompt = prompt.lower()
    reply = ""

    # Jawaban langsung berdasarkan keyword
    if "suhu" in prompt or "temperature" in prompt:
        reply = f"🌡️ Sensor saat ini mendeteksi suhu sekitar **{temp:.1f}°C**." if temp else "⚠️ Data suhu tidak tersedia."
    elif "kelembapan" in prompt or "humidity" in prompt:
        reply = f"💧 Kelembapan saat ini sekitar **{hum:.1f}%**." if hum else "⚠️ Data kelembapan tidak tersedia."
    elif "bahaya" in prompt or "alert" in prompt or "status" in prompt:
        if alert == 1:
            reply = "🚨 **Bahaya terdeteksi!** Segera lakukan pemeriksaan dan evakuasi bila perlu!"
        elif alert == 0:
            reply = "✅ Saat ini tidak terdeteksi kondisi berbahaya."
        else:
            reply = "⚠️ Status bahaya tidak bisa diambil sekarang."
    else:
        # Kirim ke Gemini dengan data sensor sebagai konteks
        reply = get_gemini_response(prompt, temp, hum, alert)

    st.chat_message("assistant").write(reply)