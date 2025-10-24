import socket
import os
import json
import time
import datetime
import random
import math
from GracefulKiller import GracefulKiller

# Initialize graceful shutdown monitor
monitor = GracefulKiller()

def simulate_current_driver():
    """
    Simulates a tachograph card reader that detects driver cards.
    Connects to the Control Unit and sends periodic updates about driver presence.
    """
    # Get Control Unit connection details from environment variables
    UC_SIMULATOR_HOST = os.getenv("UC_SIMULATOR_HOST")
    UC_SIMULATOR_PORT = int(os.getenv("UC_SIMULATOR_PORT"))
    
    # Establish TCP connection with Control Unit
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((UC_SIMULATOR_HOST, UC_SIMULATOR_PORT))
        
        # Main simulation loop
        while not monitor.kill_now:
            # Randomly determine if a driver card is present (0 or 1)
            is_driver = math.trunc(random.uniform(0.5, 1.5))
            
            if is_driver == 1:
                # If card present, randomly assign driver ID (1-3)
                driver_present = math.trunc(random.uniform(1.5, 3.5))
                simulated_driver = {
                    "Type": "CardReader",
                    "is_driver": is_driver,
                    "driver_present": f"Driver {driver_present}",
                    "Timestamp": datetime.datetime.timestamp(datetime.datetime.now()) * 1000
                }
            else:
                # If no card present
                simulated_driver = {
                    "Type": "CardReader",
                    "is_driver": is_driver,
                    "driver_present": "None", 
                    "Timestamp": datetime.datetime.timestamp(datetime.datetime.now()) * 1000
                }
            
            # Send card reader status to Control Unit
            s.sendall(bytes(json.dumps(simulated_driver), "utf-8"))
            print(f"{datetime.datetime.now()} - Sent message: {simulated_driver}")
            
            # Wait for acknowledgment from Control Unit
            data = s.recv(1024)
            print(f"{datetime.datetime.now()} - Received response: {data.decode('utf-8')}")
            
            # Wait random time before next update (0-60 seconds)
            frequency = random.uniform(0.0, 60.0)
            print(f"{datetime.datetime.now()} - Will send next message in: {frequency} seconds")
            time.sleep(frequency)

if __name__ == '__main__':
    try:
        # Start card reader simulation
        simulate_current_driver()
    except Exception as e:
        # Log any errors that occur
        print(e)
