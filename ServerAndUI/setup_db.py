import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('energy_monitor.db')
cursor = conn.cursor()

# Create the energy_usage table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS energy_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        appliance TEXT,
        power REAL,
        current REAL,
        voltage REAL,
        energy REAL
    )
''')

# Commit changes and close the connection
conn.commit()
conn.close()

print("Database and tables created successfully.")
