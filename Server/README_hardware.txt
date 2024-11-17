EE4216 Project - Hardware Server Overview

Project Overview
----------------
This Flask server records energy usage data sent from the ESP32 device. It logs readings for each appliance and sends notifications if any reading exceeds defined thresholds. Additionally, it provides a control endpoint to turn off specific appliances remotely.

Setup
-----
1. Download server dependencies, run and test endpoints to retrieve data 

Endpoints
---------
1. Upload Data Endpoint
   - Endpoint: /upload_data
   - Method: POST
   - Description: Sends energy data for each appliance to the server for logging.
   
   - All current Appliance names: ["Motor Fan", "LED Strip", "USB Charger", "Heater"]

   - Data Format:
     {
       "device": "<Appliance Name>",
       "power": <Power in Watts>,
       "current": <Current in Amps>,
       "voltage": <Voltage in Volts>
     }
   
   - Example:
     {
       "device": "Motor Fan",
       "power": 5.5,
       "current": 0.3,
       "voltage": 4.8
     }
   
   - Response:
     Success:
     {
       "status": "success",
       "message": "Data received"
     }
     
     Error:
     {
       "status": "error",
       "message": "No data received"
     }

2. Control Appliance Endpoint
   - Endpoint: /control_appliance
   - Method: POST
   - Description: Remotely turns off specific appliances via the ESP32.
   
   - Data Format:
     {
       "appliance": "<Appliance Name>"
     }
   
   - Example:
     {
       "appliance": "LED Strip"
     }
   
   - Response:
     Success:
     {
       "status": "success",
       "message": "LED Strip turned off via ESP32"
     }
     
     Error (e.g., unable to connect to ESP32):
     {
       "status": "error",
       "message": "Could not connect to ESP32"
     }


Threshold Notifications
-----------------------
When any data point exceeds thresholds for power, current, or voltage, 
an alert will be logged and an email notification will be sent automatically. Can edit ur own email
under NOTIFICATION_EMAIL to test.
