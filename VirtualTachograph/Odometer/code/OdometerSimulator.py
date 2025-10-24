# Import required libraries
import socket      # For TCP/IP communication
import os         # For environment variables
import json       # For message formatting
import time       # For sleep delays
import datetime   # For timestamps
import random     # For speed variation simulation
import math       # For mathematical operations
import threading  # For parallel execution
from GracefulKiller import GracefulKiller  # For graceful shutdown handling

# Initialize monitor for graceful shutdown
monitor = GracefulKiller()

# Global list to store speed inputs from route generator
global speed_inputs
speed_inputs = []

# Default sampling frequency in seconds
frequency = 1.0

def get_host_name():
    """Get container hostname from environment"""
    return os.getenv("HOSTNAME")

def receive_speed_inputs():
    """
    Listen for and receive speed inputs from route generator.
    Runs in a separate thread to handle incoming connections.
    """
    HOST = get_host_name()
    PORT = int(os.getenv("ODOMETER_SIMULATOR_PORT"))
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print("Odometer waiting for route generator connection...")
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            while not monitor.kill_now:
                data = conn.recv(1024)
                if not data:
                    break
                else:
                    data = data.decode("utf-8")
                    print(f"{datetime.datetime.now()} - Received message: {data}")
                    speed_inputs.append(json.loads(data))
                    conn.sendall(bytes("ok-" + str(time.time()), "utf-8"))

def simulate_current_speed():
    """
    Simulates vehicle speed readings based on route data.
    Sends measurements to Control Unit with random variations.
    Adjusts sampling frequency based on Control Unit feedback.
    """
    global frequency
    UC_SIMULATOR_HOST = os.getenv("UC_SIMULATOR_HOST")
    UC_SIMULATOR_PORT = int(os.getenv("UC_SIMULATOR_PORT"))
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((UC_SIMULATOR_HOST, UC_SIMULATOR_PORT))
        
        while not monitor.kill_now:
            # Process each speed input from route
            for speed in speed_inputs:
                # Calculate number of readings based on time and frequency
                times = math.trunc(speed["Time"] / frequency) + 1
                # Add initial random variation to speed
                random_speed = speed["Speed"] + random.uniform(-5.0, 5.0)
                
                # Generate multiple readings for current speed segment
                while times > 0:
                    # Add continuous small random variations
                    random_speed += random.uniform(-5.0, 5.0)
                    simulated_speed = {
                        "Type": "Odometer",
                        "Speed": random_speed,
                        "Timestamp": datetime.datetime.timestamp(datetime.datetime.now()) * 1000
                    }
                    
                    # Send speed reading to Control Unit
                    s.sendall(bytes(json.dumps(simulated_speed), "utf-8"))
                    print(f"{datetime.datetime.now()} - Sent message: {simulated_speed}")
                    
                    # Receive new sampling frequency from Control Unit
                    new_frequency_message = s.recv(1024)
                    new_frequency_message = new_frequency_message.decode("utf-8")
                    new_frequency_message = json.loads(new_frequency_message)
                    frequency = new_frequency_message["new_odometer_frequency"]
                    print(f"{datetime.datetime.now()} - Will send next message in: {frequency} seconds")
                    time.sleep(frequency)
                    times -= 1

if __name__ == '__main__':
    try:
        # Start thread for receiving route data
        t1 = threading.Thread(target=receive_speed_inputs, daemon=True)
        # Start thread for simulating speed readings
        t2 = threading.Thread(target=simulate_current_speed, daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        print(e)
