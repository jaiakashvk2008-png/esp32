ESP32 Wi-Fi Security Detection & Monitoring System
📌 Project Overview
This project is an ESP32-based Wi-Fi security monitoring system designed to scan nearby wireless networks, collect network information, send the data to Microsoft Azure, and display the detected networks through a live dashboard.

The long-term goal is to extend the system with machine-learning-based threat detection for Wi-Fi attacks such as Evil Twin and other suspicious network behaviors.
🏗️ System Architecture
                    ┌──────────────────────┐
                    │       ESP32          │
                    │                      │
                    │  Wi-Fi Network Scan  │
                    └──────────┬───────────┘
                               │
                               │ Telemetry JSON
                               ▼
                    ┌──────────────────────┐
                    │     Azure IoT Hub    │
                    └──────────┬───────────┘
                               │
                               │ Message Routing
                               ▼
                    ┌──────────────────────┐
                    │ Azure Blob Storage   │
                    │                      │
                    │     wifi-scans       │
                    └──────────┬───────────┘
                               │
                               │ Latest scan
                               ▼
                    ┌──────────────────────┐
                    │   Azure Function     │
                    │   get_wifi_scans     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Web Dashboard     │
                    │                      │
                    │ SSID                 │
                    │ BSSID                │
                    │ RSSI                 │
                    │ Channel              │
                    │ Security              │
                    │ Secure / Insecure    │
                    └──────────────────────┘

1. ESP32 Wi-Fi Scanner
The ESP32 performs wireless network scanning using the Arduino framework.

For every detected network, the system collects information such as:
- SSID
- BSSID
- RSSI
- Wi-Fi channel
- Security type
The ESP32 creates a telemetry payload similar to:
{
  "device": "ESP32-Security-Sensor",
  "scanCount": 15,
  "networkCount": 2,
  "networks": [
    {
      "ssid": "ExampleWiFi",
      "bssid": "AA:BB:CC:DD:EE:FF",
      "rssi": -45,
      "channel": 6,
      "security": "SECURED"
    }
  ]
}

The ESP32 then publishes this telemetry to Azure.
2. Azure IoT Hub
Azure IoT Hub acts as the communication layer between the ESP32 and Azure.
ESP32
  ↓
Wi-Fi
  ↓
Azure IoT Hub

The ESP32 publishes telemetry messages using MQTT.

Successful publishing produces a message such as:
Message published successfully

3. Azure Blob Storage
IoT Hub routes the telemetry into an Azure Blob Storage container.

Current container:
wifi-scans

The stored files are JSON blobs.

The Azure-stored message currently uses an outer structure where the ESP32 telemetry can appear inside the Body field as Base64-encoded data.

The Python/Node.js backend decodes this data to obtain the actual Wi-Fi scan.
4. Current Wi-Fi Data
The collected data contains information such as:
SSID
BSSID
RSSI
Channel
Security

The current dataset also contains derived fields used for future ML work, including:
is_open
is_wpa2
is_unknown_security
same_ssid_count
same_ssid_distinct_bssids
same_ssid_security_mismatch
label

The current training CSV contains normal Wi-Fi observations, but the label field is currently not populated with confirmed Evil Twin examples.

Therefore, the final supervised ML classifier has not yet been trained.
5. Current Dashboard
The first version of the dashboard is intentionally simple.

It should display the networks currently detected by the ESP32.

Example:
SSID	BSSID	RSSI	Channel	Security	Status
ExampleWiFi	AA:BB:CC...	-45	6	SECURED	🟢 SECURE
TestNetwork	DD:EE:FF...	-72	11	OPEN	🔴 INSECURE


The current rule is:
security == "SECURED"
        ↓
     SECURE

anything else
        ↓
    INSECURE

This does not mean that an INSECURE network is malicious. It only represents the current security classification rule.
6. Live Monitoring
The intended behavior is:
ESP32 scans
     ↓
New telemetry
     ↓
Azure
     ↓
Dashboard retrieves latest data
     ↓
Dashboard updates

When the ESP32 is moved to another location and detects additional networks, those observations should appear in the dashboard after the new telemetry reaches Azure.

Example:
Location A

WiFi-A
WiFi-B
WiFi-C

Move ESP32:
Location B

WiFi-D
WiFi-E
WiFi-F
WiFi-G

The dashboard should reflect the new scan results.
7. Azure Function
The project currently contains an Azure Function:
get_wifi_scans

Its purpose is to act as an API between the dashboard and Azure Blob Storage.
Dashboard
    ↓
HTTP request
    ↓
get_wifi_scans
    ↓
Azure Blob Storage
    ↓
Latest ESP32 scan
    ↓
JSON response
    ↓
Dashboard

The Function App uses environment/application settings rather than putting the Azure Storage connection string directly into the source code.

Required settings:
AZURE_STORAGE_CONTAINER
wifi-scans

AZURE_STORAGE_CONNECTION_STRING
<secret>

Never commit the connection string to GitHub or put it directly into source code.
8. Machine Learning — Planned
Machine learning is a separate phase of the project.

The intended pipeline is:
Wi-Fi observations
        ↓
Data preparation
        ↓
Labeled dataset
        ↓
Feature extraction
        ↓
Machine Learning model
        ↓
Prediction
        ↓
Dashboard

The model will eventually classify network observations based on features extracted from the Wi-Fi scan.

The project is intended to investigate suspicious Wi-Fi behavior including:
- Evil Twin
- Rogue access points
- Suspicious duplicate SSIDs
- Security mismatches
- Other Wi-Fi-related anomalies
The exact attacks that can be reliably detected will depend on the available training data and features.
9. Evil Twin Training Data
A controlled test environment will be used to create labeled examples.

Conceptually:
Legitimate AP
      +
Controlled test Evil Twin AP
      ↓
ESP32 scans
      ↓
Azure
      ↓
Training dataset
      ↓
Labels
      ↓
ML training

The important requirement is that the training data has known ground truth.

For example:
LEGITIMATE
LEGITIMATE
LEGITIMATE
FAKE
FAKE
FAKE

We should not randomly label normal networks as malicious simply to create a training dataset.
10. Training vs Live Detection
These are two different processes.
Training
Historical labeled data
        ↓
train_model.py
        ↓
Trained model

Training happens separately.
Live detection
ESP32
 ↓
Azure
 ↓
New scan
 ↓
Trained model
 ↓
Prediction
 ↓
Dashboard

The live system should not retrain the model every time the ESP32 moves to a different location.
11. Project Components
Current/planned components:
ESP32
Arduino IDE
Azure IoT Hub
Azure Blob Storage
Azure Function
Web Dashboard
Python data-processing pipeline
Machine Learning model

12. Project Status
✅ Completed
- ESP32 Wi-Fi scanning
- Wi-Fi information collection
- JSON telemetry generation
- Azure IoT Hub connection
- Telemetry publishing
- Azure Blob Storage integration
- JSON data appearing in Azure Blob Storage
- Azure Storage connection from the local Python environment
- Initial training CSV generation
- Azure Function App creation
- get_wifi_scans HTTP function creation
- Azure application settings for Blob Storage
🔄 Currently building
- Azure Function → Blob Storage integration
- Live web dashboard
- Real-time/latest Wi-Fi display
- Secure/Insecure classification
⏳ Planned
- Controlled Evil Twin dataset
- Proper labeling
- ML model training
- Threat/anomaly detection
- ML predictions in dashboard
- Confidence/suspicion score
- Detection history
- Better security classification
- Support for multiple Wi-Fi attack indicators
13. Final Vision
The final system is intended to work like this:
                         ┌──────────────┐
                         │    ESP32     │
                         │ Wi-Fi Scanner│
                         └──────┬───────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Azure IoT Hub │
                       └────────┬────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Azure Blob      │
                       │ Storage         │
                       └────────┬────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Azure Function  │
                       │                 │
                       │ Data Processing │
                       └────────┬────────┘
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
                 ▼                             ▼
        ┌─────────────────┐           ┌─────────────────┐
        │ Security Rules  │           │ ML Threat Model │
        └────────┬────────┘           └────────┬────────┘
                 │                             │
                 └──────────────┬──────────────┘
                                ▼
                       ┌─────────────────┐
                       │    Dashboard    │
                       │                 │
                       │ Wi-Fi Networks  │
                       │ Secure/Insecure │
                       │ Threat Status   │
                       │ ML Confidence   │
                       └─────────────────┘

🎯 Project Goal
Build a cloud-connected ESP32 Wi-Fi security monitoring system that can scan wireless networks, send observations to Azure, display them in a live dashboard, and eventually use machine learning and security rules to identify potentially suspicious Wi-Fi networks and attacks.

Current priority: finish the live Azure dashboard first. ML training comes afterward.
