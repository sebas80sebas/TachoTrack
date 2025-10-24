# Import required libraries
import os         # For environment variables
import socket    # For TCP/IP communication
import json      # For message formatting
import time      # For sleep delays
import threading # For parallel execution
import datetime  # For timestamps
import random    # For simulation variations
import math      # For mathematical operations
from GracefulKiller import GracefulKiller  # For graceful shutdown handling

# Initialize monitor for graceful shutdown
monitor = GracefulKiller()

# Default sampling frequency in seconds
frequency = 1.0

def get_host_name():
    """Get container hostname from environment"""
    return os.getenv("HOSTNAME")

def receive_simulation_inputs():
    """
    Listen for and receive position/route data from route generator.
    Stores received coordinates and speeds in global simulation_inputs list.
    """
    global simulation_inputs
    simulation_inputs = []
    HOST = get_host_name()
    PORT = int(os.getenv("GNSS_SIMULATOR_PORT"))
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
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
                    simulation_inputs.append(json.loads(data))
                    conn.sendall(bytes("ok-" + str(time.time()), "utf-8"))

def simulate_positioning():
    """
    Simulates GNSS positioning system.
    Sends position and speed data to Control Unit.
    Adjusts sampling frequency based on Control Unit feedback.
    """
    global frequency
    UC_SIMULATOR_HOST = os.getenv("UC_SIMULATOR_HOST")
    UC_SIMULATOR_PORT = int(os.getenv("UC_SIMULATOR_PORT"))
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((UC_SIMULATOR_HOST, UC_SIMULATOR_PORT))
        
        while not monitor.kill_now:
            # Process each position/route segment
            for position in simulation_inputs:
                # Calculate number of position updates based on time and frequency
                times = math.trunc(position["Time"] / frequency) + 1
                
                # Send intermediate position updates
                while times - 1 > 0:
                    simulated_position = {
                        "Type": "GPS",
                        "Position": position["Origin"],
                        "Speed": position["Speed"],
                        "Timestamp": datetime.datetime.timestamp(datetime.datetime.now()) * 1000
                    }
                    
                    # Send position data to Control Unit
                    s.sendall(bytes(json.dumps(simulated_position), "utf-8"))
                    print(f"{datetime.datetime.now()} - Sent message: {simulated_position}")
                    
                    # Receive updated sampling frequency from Control Unit
                    new_frequency_message = s.recv(1024)
                    new_frequency_message = new_frequency_message.decode("utf-8")
                    new_frequency_message = json.loads(new_frequency_message)
                    frequency = new_frequency_message["new_gnss_frequency"]
                    print(f"{datetime.datetime.now()} - Will send next message in: {frequency} seconds")
                    time.sleep(frequency)
                    times -= 1
                
                # Send final destination position
                last_position = position["Destination"]
                simulated_position = {
                    "Type": "GPS",
                    "Position": last_position,
                    "Speed": position["Speed"],
                    "Timestamp": datetime.datetime.timestamp(datetime.datetime.now()) * 1000
                }
                
                s.sendall(bytes(json.dumps(simulated_position), "utf-8"))
                print(f"{datetime.datetime.now()} - Sent message: {simulated_position}")
                
                # Receive updated sampling frequency from Control Unit
                new_frequency_message = s.recv(1024)
                new_frequency_message = new_frequency_message.decode("utf-8")
                new_frequency_message = json.loads(new_frequency_message)
                frequency = new_frequency_message["new_gnss_frequency"]
                print(f"{datetime.datetime.now()} - Will send next message in: {frequency} seconds")
                time.sleep(frequency)

if __name__ == '__main__':
    try:
        # Start thread for receiving route data
        t1 = threading.Thread(target=receive_simulation_inputs, daemon=True)
        t1.start()
        # Start thread for simulating positioning
        t2 = threading.Thread(target=simulate_positioning, daemon=True)
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        print(e)

