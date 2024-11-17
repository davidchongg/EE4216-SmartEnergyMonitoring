EE4216 Project - UI/Analytics Server Overview

Project Overview
----------------
This Flask API provides various endpoints to retrieve energy consumption data for appliances over the last 24 hours. 
It current fns include viewing the latest readings, calculating average power, total energy consumption, and estimating energy costs.

Setup
-----
1. Download server dependencies, run and test endpoints to retrieve data 

Available Endpoints
-------------------
1. Latest Data Endpoint
   - Endpoint: /latest_data
   - Method: GET
   - Description: Retrieves the latest readings for each appliance, including optional filters for fields and appliance.
   
   - Query Parameters:
     - appliance (optional): Filter by appliance name (e.g., ?appliance=Motor Fan).
     - fields (optional): Specify which fields to retrieve (e.g., ?fields=power,current).
     - if no added fields, it will just return all latest values
   
   - Example: GET /latest_data?fields=power,current
   
   - Response:
     [
       {
         "appliance": "Motor Fan",
         "timestamp": "2024-11-01 12:00:00",
         "power": 5.5,
         "current": 0.3
       },
       {
         "appliance": "LED Strip",
         "timestamp": "2024-11-01 12:00:00",
         "power": 1.2,
         "current": 0.05
       }
     ]

2. Average Power Consumption
   - Endpoint: /average_power
   - Method: GET
   - Description: Calculates the average power consumption for each appliance over the last 24 hours.
   
   - Response:
     [
       {
         "appliance": "Motor Fan",
         "average_power": 5.4
       },
       {
         "appliance": "LED Strip",
         "average_power": 1.1
       }
     ]

3. Total Energy Consumption
   - Endpoint: /total_energy
   - Method: GET
   - Description: Returns the total energy consumed by each appliance in watt-hours over the last 24 hours.
   
   - Response:
     [
       {
         "appliance": "Motor Fan",
         "total_energy_wh": 130.0
       },
       {
         "appliance": "LED Strip",
         "total_energy_wh": 24.0
       }
     ]

4. Energy Cost Estimation
   - Endpoint: /energy_cost
   - Method: GET
   - Description: Estimates the energy cost per appliance over the last 24 hours based on a cost of energy per kWh.
   
   - Response:
     [
       {
         "appliance": "Motor Fan",
         "energy_cost": 0.0416
       },
       {
         "appliance": "LED Strip",
         "energy_cost": 0.0077
       }
     ]

5. Power Usage Data for the Last 24 Hours
   - Endpoint: /power_usage_last_24h
   - Method: GET
   - Description: Retrieves all power readings for each appliance over the last 24 hours, useful for generating time series graphs.
   
   - Response:
     {
       "Motor Fan": [
         {"timestamp": "2024-11-01 08:00:00", "power": 5.4},
         {"timestamp": "2024-11-01 09:00:00", "power": 5.6}
       ],
       "LED Strip": [
         {"timestamp": "2024-11-01 08:00:00", "power": 1.2},
         {"timestamp": "2024-11-01 09:00:00", "power": 1.1}
       ]
     }

6. Control Appliance
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

Appliance Names
---------------
Use one of the following appliance names as values for any appliance-related queries:
- Motor Fan
- LED Strip
- USB Charger
- Heater
