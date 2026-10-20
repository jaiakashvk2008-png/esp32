import os
import json
import base64
from datetime import datetime

from flask import Flask, jsonify, render_template_string
from azure.storage.blob import BlobServiceClient


app = Flask(__name__)

# --------------------------------------------------
# AZURE CONFIGURATION
# --------------------------------------------------

AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "wifi-scans")

if not AZURE_CONNECTION_STRING:
    raise RuntimeError(
        "AZURE_STORAGE_CONNECTION_STRING is not set."
    )

blob_service = BlobServiceClient.from_connection_string(
    AZURE_CONNECTION_STRING
)

container_client = blob_service.get_container_client(
    AZURE_CONTAINER
)


# --------------------------------------------------
# GET LATEST ESP32 SCAN FROM AZURE
# --------------------------------------------------

def get_latest_scan():

    blobs = list(container_client.list_blobs())

    if not blobs:
        return {
            "device": "ESP32-Security-Sensor",
            "scanCount": 0,
            "networkCount": 0,
            "networks": []
        }

    # Newest blob first
    blobs.sort(
        key=lambda blob: blob.last_modified,
        reverse=True
    )

    latest_blob = blobs[0]

    print("Reading:", latest_blob.name)

    blob_client = container_client.get_blob_client(
        latest_blob.name
    )

    raw_data = blob_client.download_blob().readall()

    outer_json = json.loads(raw_data)

    # --------------------------------------------------
    # Azure IoT Hub routed message format
    # The actual ESP32 JSON is inside "Body"
    # --------------------------------------------------

    if "Body" in outer_json:

        body = outer_json["Body"]

        # Body is Base64 encoded
        if isinstance(body, str):

            try:
                decoded = base64.b64decode(body).decode("utf-8")
                scan_data = json.loads(decoded)

            except Exception as e:
                print("Base64 decoding failed:", e)

                # Try direct JSON just in case
                try:
                    scan_data = json.loads(body)
                except Exception:
                    return {
                        "device": "ESP32-Security-Sensor",
                        "scanCount": 0,
                        "networkCount": 0,
                        "networks": []
                    }

        else:
            scan_data = body

    else:
        # In case Azure contains the ESP32 JSON directly
        scan_data = outer_json

    # Add information about the Azure blob
    scan_data["_azure_blob"] = latest_blob.name
    scan_data["_azure_time"] = str(latest_blob.last_modified)

    return scan_data


# --------------------------------------------------
# PROCESS NETWORKS
# --------------------------------------------------

def get_networks():

    scan = get_latest_scan()

    networks = []

    for network in scan.get("networks", []):

        security = str(
            network.get("security", "")
        ).upper().strip()

        # YOUR RULE:
        # SECURED = Secure
        # Anything else = Insecure

        if security == "SECURED":
            status = "SECURE"
        else:
            status = "INSECURE"

        networks.append({
            "ssid": network.get("ssid", "Unknown"),
            "bssid": network.get("bssid", "Unknown"),
            "rssi": network.get("rssi", 0),
            "channel": network.get("channel", 0),
            "security": security,
            "status": status
        })

    return {
        "device": scan.get(
            "device",
            "ESP32-Security-Sensor"
        ),
        "scanCount": scan.get(
            "scanCount",
            0
        ),
        "networkCount": len(networks),
        "networks": networks,
        "azureBlob": scan.get(
            "_azure_blob",
            ""
        ),
        "azureTime": scan.get(
            "_azure_time",
            ""
        )
    }


# --------------------------------------------------
# API
# --------------------------------------------------

@app.route("/api/networks")
def api_networks():

    try:
        data = get_networks()
        return jsonify(data)

    except Exception as e:

        print("ERROR:", e)

        return jsonify({
            "error": str(e),
            "networks": []
        }), 500


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

HTML = """
<!DOCTYPE html>

<html>

<head>

    <title>ESP32 Wi-Fi Security Dashboard</title>

    <meta name="viewport"
          content="width=device-width, initial-scale=1">

    <style>

        body {
            font-family: Arial, sans-serif;
            background: #f4f6f8;
            margin: 0;
            padding: 30px;
        }

        h1 {
            margin-bottom: 5px;
        }

        .subtitle {
            color: #666;
            margin-bottom: 25px;
        }

        .stats {
            display: flex;
            gap: 15px;
            margin-bottom: 25px;
        }

        .card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            min-width: 160px;
        }

        .number {
            font-size: 30px;
            font-weight: bold;
        }

        .label {
            color: #777;
            margin-top: 5px;
        }

        table {
            width: 100%;
            background: white;
            border-collapse: collapse;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }

        th, td {
            padding: 14px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }

        th {
            background: #202938;
            color: white;
        }

        .secure {
            color: #16803c;
            font-weight: bold;
        }

        .insecure {
            color: #d62828;
            font-weight: bold;
        }

        .dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 6px;
        }

        .green {
            background: #16803c;
        }

        .red {
            background: #d62828;
        }

        .footer {
            margin-top: 20px;
            color: #777;
            font-size: 13px;
        }

    </style>

</head>


<body>

    <h1>ESP32 Wi-Fi Security Dashboard</h1>

    <div class="subtitle">
        Live Wi-Fi observations from Azure Blob Storage
    </div>


    <div class="stats">

        <div class="card">
            <div class="number" id="networkCount">0</div>
            <div class="label">Networks Detected</div>
        </div>

        <div class="card">
            <div class="number" id="secureCount">0</div>
            <div class="label">Secure</div>
        </div>

        <div class="card">
            <div class="number" id="insecureCount">0</div>
            <div class="label">Insecure</div>
        </div>

        <div class="card">
            <div class="number" id="scanCount">0</div>
            <div class="label">Scan Number</div>
        </div>

    </div>


    <table>

        <thead>

            <tr>
                <th>SSID</th>
                <th>BSSID</th>
                <th>RSSI</th>
                <th>Channel</th>
                <th>Security</th>
                <th>Status</th>
            </tr>

        </thead>

        <tbody id="networkTable">

        </tbody>

    </table>


    <div class="footer">

        Last Azure blob:
        <span id="azureBlob">Waiting...</span>

        <br>

        Last update:
        <span id="updateTime">Waiting...</span>

    </div>


<script>

async function updateDashboard() {

    try {

        const response =
            await fetch("/api/networks");

        const data =
            await response.json();


        if (data.error) {

            console.error(data.error);
            return;

        }


        document.getElementById(
            "networkCount"
        ).textContent = data.networkCount;


        document.getElementById(
            "scanCount"
        ).textContent = data.scanCount;


        let secure = 0;
        let insecure = 0;


        const table =
            document.getElementById(
                "networkTable"
            );

        table.innerHTML = "";


        data.networks.forEach(network => {

            if (network.status === "SECURE") {
                secure++;
            } else {
                insecure++;
            }


            const row =
                document.createElement("tr");


            const statusClass =
                network.status === "SECURE"
                ? "secure"
                : "insecure";


            const dotClass =
                network.status === "SECURE"
                ? "green"
                : "red";


            row.innerHTML = `

                <td>
                    ${network.ssid}
                </td>

                <td>
                    ${network.bssid}
                </td>

                <td>
                    ${network.rssi} dBm
                </td>

                <td>
                    ${network.channel}
                </td>

                <td>
                    ${network.security}
                </td>

                <td class="${statusClass}">

                    <span class="dot ${dotClass}">
                    </span>

                    ${network.status}

                </td>

            `;


            table.appendChild(row);

        });


        document.getElementById(
            "secureCount"
        ).textContent = secure;


        document.getElementById(
            "insecureCount"
        ).textContent = insecure;


        document.getElementById(
            "azureBlob"
        ).textContent =
            data.azureBlob;


        document.getElementById(
            "updateTime"
        ).textContent =
            new Date().toLocaleTimeString();


    } catch (error) {

        console.error(
            "Dashboard update failed:",
            error
        );

    }

}


// First update
updateDashboard();


// Check Azure every 3 seconds
setInterval(
    updateDashboard,
    3000
);

</script>

</body>

</html>
"""


@app.route("/")
def dashboard():
    return render_template_string(HTML)


# --------------------------------------------------
# START SERVER
# --------------------------------------------------

if __name__ == "__main__":

    print("")
    print("======================================")
    print(" ESP32 WI-FI SECURITY DASHBOARD")
    print("======================================")
    print("")
    print("Azure container:", AZURE_CONTAINER)
    print("Dashboard: http://127.0.0.1:5000")
    print("")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
