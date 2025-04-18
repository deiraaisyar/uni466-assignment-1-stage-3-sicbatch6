# Samsung Innovation Campus Batch 6 Stage 3 Assignment
![Header](/HelmAware_Header.jpg)
## General Information
Group Name: Warga Naget

Group Code: UNI466

Group Members:
- Deira Aisya Refani
- Finanazwa Ayesha
- Regina Joan Medea Jati Laksono
- Yusuf Imantaka Bastari

## Project Overview
This project is called HelmAware, an end-to-end IoT solution designed for worker safety monitoring in construction environments. It integrates an ESP32 microcontroller (with and without camera), a Flask/Streamlit-based application, Ubidots for cloud visualization, and a YOLOv8 object detection model for hazard alerts.

The system collects temperature, humidity, and motion data from an ESP32 board and streams camera footage for object detection. Data is visualized and monitored via a custom dashboard, with alerts and recommendations generated in real-time.

### Key Features
- Streamlit-Based Web App (Python):

  Real-time dashboard for displaying temperature, humidity, motion, and video stream from ESP32-CAM.

  Hazard detection using YOLOv8 based on bounding box area.

  Interactive chatbot powered by Gemini API for safety insights and Q&A.

- ESP32 + ESP32-CAM Microcontrollers:

  ESP32 reads and sends sensor data (temperature, humidity, motion) to Ubidots via HTTP.

  ESP32-CAM streams video over IP to the Streamlit dashboard.

  Manual and automatic triggering of alert signals based on object detection.

- Ubidots Cloud Integration:

  Displays real-time and historical data for environmental monitoring.

  Acts as a broker for MQTT-based alert signals.

  Provides switch control and live sensor variable storage.

- Hazard Detection with YOLOv8:

  Object detection on live camera feed to identify human presence.

  Alerts are triggered based on object size (area threshold) to warn of proximity danger.

- AI Chatbot Integration:

  Gemini-based assistant provides dynamic responses based on latest sensor data.

  Can explain safety conditions or respond to custom prompts using real-time info.

### How It Works
1. Sensor Data Acquisition:

  An ESP32 reads temperature, humidity, and motion sensor values and sends them to Ubidots via HTTP POST.

2. Data Visualization & Monitoring:

  The Python dashboard (Streamlit) fetches this data from Ubidots and displays it in real time as metrics and charts.

3. Camera Stream & Detection:

  ESP32-CAM streams MJPEG video, which is read by the app.

  YOLOv8 model runs locally to detect "person" class; if a person is too close (bounding box area exceeds threshold), it triggers an alert.

4. Alert Mechanism:

  Alerts are sent to Ubidots (via MQTT) and displayed in the dashboard when hazards are detected.

  Alerts auto-reset if no hazard is detected after a configurable delay.

5. Cloud Dashboard (Ubidots):

  Ubidots stores all sensor data and displays it with graphs and widgets.

  A switch (virtual variable) can be toggled remotely for testing or device control.

7. AI Assistant:

  Users can interact with the chatbot to ask about temperature, humidity, alert status, or general safety guidance.

  Responses are contextualized using the latest sensor readings.




Ubidots Link: https://stem.ubidots.com/app/dashboards/public/dashboard/KgbDk-BLMrFIxYlufbDPBy5SNaQIkMPOrjdkDeK8qlM?navbar=true&contextbar=true&datePicker=true&devicePicker=true&displayTitle=true



Video Demonstration Link: https://youtu.be/WJNQb5I8uZY

