from flask import Flask, request, jsonify
from flask import send_from_directory
import os
import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

app = Flask(__name__)

APPLIANCES = ["Motor Fan", "LED Strip", "USB Charger", "Washing Machine"]
ESP32_IP = "http://192.168.1.16"  # Replace <ESP32_IP_ADDRESS> with the actual IP address of your ESP32
COST_PER_KWH = 0.32  # Cost per kWh

# Threshold values for notifications
POWER_THRESHOLD = 998.0  # in watts
CURRENT_THRESHOLD = 990.5  # in amps
VOLTAGE_THRESHOLD = 599.0  # in volts

# Email configuration
EMAIL_ADDRESS = "ee4216projectgroup3@gmail.com"
EMAIL_PASSWORD = "lpid wkrj ftrf jplu"
NOTIFICATION_EMAIL = "gladysxxc@gmail.com"

def send_email(subject, message):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = NOTIFICATION_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")

# Insert data and check thresholds
def insert_energy_data(appliance, power, current, voltage):
    conn = sqlite3.connect('energy_monitor.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS energy_usage (
                        timestamp TEXT,
                        appliance TEXT,
                        power REAL,
                        current REAL,
                        voltage REAL,
                        energy REAL
                      )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS notifications (
                        timestamp TEXT,
                        message TEXT
                      )''')
    # Get the last timestamp for this appliance
    cursor.execute('SELECT timestamp FROM energy_usage WHERE appliance = ? ORDER BY timestamp DESC LIMIT 1', (appliance,))
    last_entry = cursor.fetchone()
    current_timestamp = datetime.now()
    
    if last_entry:
        last_timestamp = datetime.strptime(last_entry[0], "%Y-%m-%d %H:%M:%S")
        delta_t = (current_timestamp - last_timestamp).total_seconds() / 3600.0  # in hours
    else:
        delta_t = 0  # First entry for this appliance
    
    # Calculate energy (Wh)
    energy = power * delta_t

    timestamp_str = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''INSERT INTO energy_usage (timestamp, appliance, power, current, voltage, energy)
                      VALUES (?, ?, ?, ?, ?, ?)''', 
                   (timestamp_str, appliance, power, current, voltage, energy))
    conn.commit()
    conn.close()
    
    # Threshold checks
    if power > POWER_THRESHOLD or current > CURRENT_THRESHOLD or voltage > VOLTAGE_THRESHOLD:
        alert_message = []
        if power > POWER_THRESHOLD:
            alert_message.append(f"Power threshold breached for {appliance}: {power}W")
        if current > CURRENT_THRESHOLD:
            alert_message.append(f"Current threshold breached for {appliance}: {current}A")
        if voltage > VOLTAGE_THRESHOLD:
            alert_message.append(f"Voltage threshold breached for {appliance}: {voltage}V")
        
        alert_message = "\n".join(alert_message)
        send_notification(alert_message)
        send_email("Threshold Alert", alert_message)

def send_notification(message):
    conn = sqlite3.connect('energy_monitor.db')
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''INSERT INTO notifications (timestamp, message) VALUES (?, ?)''', 
                   (timestamp, message))
    conn.commit()
    conn.close()

@app.route('/')
def serve_html():
    return send_from_directory(os.getcwd(), 'index.html')

# Control endpoint to turn on/off specific appliances
@app.route('/control_appliance', methods=['POST'])
def control_appliance():
    data = request.json
    appliance = data.get("appliance")
    action = data.get("action")
    
    # Use form-encoded data instead of JSON
    payload = {
        "appliance": appliance,
        "action": action
    }
    
    try:
        # Send a form-encoded POST request instead of JSON
        response = requests.post(f"{ESP32_IP}/control", data=payload)
        if response.ok:
            return jsonify({"status": "success", "message": f"{appliance} {action} successfully."}), 200
        else:
            return jsonify({"status": "error", "message": f"Failed to {action} {appliance} on ESP32"}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({"status": "error", "message": f"ESP32 connection failed: {e}"}), 500

# Endpoint to receive data from ESP32
@app.route('/upload_data', methods=['POST'])
def upload_data():
    data = request.json
    if data:
        appliance = data.get('device')
        power = float(data.get('power'))
        current = float(data.get('current'))
        voltage = float(data.get('voltage'))
        insert_energy_data(appliance, power, current, voltage)
        return jsonify({'status': 'success', 'message': 'Data received'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'No data received'}), 400

# Total energy usage for last 1 hour
@app.route('/power_usage_last_1h', methods=['GET'])
def total_power_last_1h():
    conn = sqlite3.connect('energy_monitor.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT appliance, SUM(energy) FROM energy_usage
        WHERE timestamp >= datetime("now", "-1 hour", 'localtime')
        GROUP BY appliance
    ''')
    data = cursor.fetchall()
    conn.close()
    return jsonify([{'appliance': row[0], 'total_energy_wh': row[1]} for row in data])

# Total energy usage for last 24 hours
@app.route('/power_usage_last_24h', methods=['GET'])
def total_power_last_24h():
    conn = sqlite3.connect('energy_monitor.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT appliance, SUM(energy) FROM energy_usage
        WHERE timestamp >= datetime("now", "-24 hours", 'localtime')
        GROUP BY appliance
    ''')
    data = cursor.fetchall()
    conn.close()
    return jsonify([{'appliance': row[0], 'total_energy_wh': row[1]} for row in data])

@app.route('/detailed_power_usage_last_24h', methods=['GET'])
def detailed_power_usage_last_24h():
    conn = sqlite3.connect('energy_monitor.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT appliance, timestamp, power FROM energy_usage
        WHERE timestamp >= datetime("now", "-24 hours", 'localtime')
        ORDER BY appliance, timestamp
    ''')
    data = cursor.fetchall()
    conn.close()
    
    # Organize data by appliance for easier rendering
    result = {}
    for row in data:
        appliance, timestamp, power = row
        if appliance not in result:
            result[appliance] = []
        result[appliance].append({
            "timestamp": timestamp,
            "power": power
        })
    
    return jsonify(result)


@app.route('/detailed_power_usage_last_1h', methods=['GET'])
def detailed_power_usage_last_1h():
    conn = sqlite3.connect('energy_monitor.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT appliance, timestamp, power FROM energy_usage
        WHERE timestamp >= datetime("now", "-1 hours", 'localtime')
        ORDER BY appliance, timestamp
    ''')
    data = cursor.fetchall()
    conn.close()

    # Organize data by appliance for easier rendering
    result = {}
    for row in data:
        appliance, timestamp, power = row
        if appliance not in result:
            result[appliance] = []
        result[appliance].append({
            "timestamp": timestamp,
            "power": power
        })

    return jsonify(result)

# Cost analysis for last 24 hours
@app.route('/cost_per_appliance_24h', methods=['GET'])
def cost_per_appliance_24h():
    conn = sqlite3.connect('energy_monitor.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT appliance, SUM(energy) FROM energy_usage
        WHERE timestamp >= datetime("now", "-24 hours", 'localtime')
        GROUP BY appliance
    ''')
    data = cursor.fetchall()
    conn.close()
    
    result = []
    for row in data:
        appliance = row[0]
        total_energy_kwh = row[1] / 1000.0  # Convert Wh to kWh
        cost = total_energy_kwh * COST_PER_KWH
        result.append({'appliance': appliance, 'cost_sgd': cost})
    
    return jsonify(result)

# Cost analysis for last 7 days
@app.route('/cost_per_appliance_7d', methods=['GET'])
def cost_per_appliance_7d():
    conn = sqlite3.connect('energy_monitor.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT appliance, SUM(energy) FROM energy_usage
        WHERE timestamp >= datetime("now", "-168 hours", 'localtime')
        GROUP BY appliance
    ''')
    data = cursor.fetchall()
    conn.close()

    result = []
    for row in data:
        appliance = row[0]
        total_energy_kwh = row[1] / 1000.0  # Convert Wh to kWh
        cost = total_energy_kwh * COST_PER_KWH
        result.append({'appliance': appliance, 'cost_sgd': cost})

    return jsonify(result)

@app.route('/recent_data', methods=['GET'])
def recent_data():
    try:
        conn = sqlite3.connect('energy_monitor.db')
        cursor = conn.cursor()

        # Updated query with 'appliance' instead of 'device'
        cursor.execute('''
            SELECT appliance, power, current, voltage, timestamp
            FROM energy_usage
            WHERE timestamp = (
                SELECT MAX(timestamp)
                FROM energy_usage AS inner_table
                WHERE inner_table.appliance = energy_usage.appliance
            )
        ''')
        rows = cursor.fetchall()
        conn.close()

        # Debug: Print fetched rows
        print("Fetched rows:", rows)

        # Format the result
        result = {row[0]: {
            'power': row[1] or 0,
            'current': row[2] or 0,
            'voltage': row[3] or 0,
            'timestamp': row[4] or "Unknown"
        } for row in rows}

        return jsonify(result)
    except Exception as e:
        # Log and return the error
        print(f"Error fetching recent data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
