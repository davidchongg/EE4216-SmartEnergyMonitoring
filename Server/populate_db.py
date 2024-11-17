import sqlite3
from datetime import datetime, timedelta
import random

# Database setup
DB_NAME = 'energy_monitor.db'

# Define appliances, their general power consumption characteristics, and probabilities of being turned on
appliances = {
    "Motor Fan": {"avg_power": 500, "avg_current": 0.5, "on_probability": 4},  # 70% chance of being on
    "LED Strip": {"avg_power": 250, "avg_current": 0.1, "on_probability": 2},  # 50% chance of being on
    "USB Charger": {"avg_power": 750, "avg_current": 0.2, "on_probability": 10},  # 90% chance of being on
    "Washing Machine": {"avg_power": 800, "avg_current": 0.8, "on_probability": 1},  # 20% chance of being on
}

# Track appliances' remaining on-duration
appliance_durations = {appliance: 0 for appliance in appliances}

# Generate data for the past 100 hours, every 15 minutes
def generate_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Start time: 100 hours ago
    timestamp = datetime.now() - timedelta(hours=100)

    while timestamp < datetime.now():
        for appliance, details in appliances.items():
            # Check if the appliance is currently on
            if appliance_durations[appliance] > 0:
                # Generate appliance readings
                avg_power = details["avg_power"]
                avg_current = details["avg_current"]

                power = round(random.uniform(avg_power * 0.9, avg_power * 1.1), 2)  # ±10% variation
                current = round(random.uniform(avg_current * 0.9, avg_current * 1.1), 2)  # ±10% variation
                voltage = round(random.uniform(4.5, 5.0), 2)  # Random voltage between 4.5V and 5V
                energy = round(power * 0.25, 2)  # Energy in Wh (Power in W * Time in hours)

                # Insert data into the table
                cursor.execute('''
                    INSERT INTO energy_usage (timestamp, appliance, power, current, voltage, energy)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (timestamp.strftime("%Y-%m-%d %H:%M:%S"), appliance, power, current, voltage, energy))

                # Decrease the remaining on-duration
                appliance_durations[appliance] -= 1

                # Debugging output
                print(f"{appliance} ON: Power={power}W, Current={current}A, Voltage={voltage}V, Energy={energy}Wh, Remaining Steps={appliance_durations[appliance]}")
            else:
                # Set power, voltage, and current to 0 if the appliance is off
                power = 0
                current = 0
                voltage = 0
                energy = 0

                # Determine if the appliance turns on this time step
                if random.randint(1, 100) <= details["on_probability"]:
                    appliance_durations[appliance] = random.randint(5, 10)  # Random duration (5-10 steps)
                    print(f"{appliance} turned ON for {appliance_durations[appliance]} steps")
                else:
                    print(f"{appliance} OFF")

                # Insert data into the table with zero values for OFF appliances
                cursor.execute('''
                    INSERT INTO energy_usage (timestamp, appliance, power, current, voltage, energy)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (timestamp.strftime("%Y-%m-%d %H:%M:%S"), appliance, power, current, voltage, energy))

        # Increment timestamp by 15 minutes
        timestamp += timedelta(minutes=15)

    conn.commit()
    conn.close()
    print("Database populated with sample data.")

# Run data generation
generate_data()
