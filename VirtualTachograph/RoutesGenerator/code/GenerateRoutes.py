# Import required libraries
import threading  # For parallel execution
import socket    # For TCP/IP communication
import json      # For message formatting
import time      # For delays
import os        # For environment variables
import requests  # For HTTP requests
import datetime  # For timestamps
from math import acos, cos, sin, radians  # For geographical calculations
from GracefulKiller import GracefulKiller  # For graceful shutdown handling

# Initialize monitor for graceful shutdown
monitor = GracefulKiller()

def generate_route_simulations(origin_address, destination_address):
    """
    Generate route simulations between two addresses using Google Routes API
    Args:
        origin_address: Starting location address
        destination_address: Ending location address
    Returns:
        Tuple containing lists of positions and speeds to simulate
    """
    print("Assigning a route to the vehicle")
    
    # Prepare API request body
    my_body = {
        "origin": {"address": origin_address},
        "destination": {"address": destination_address},
        "travelMode": "DRIVE",
        "languageCode": "es-ES",
        "units": "METRIC"
    }
    
    # Set API request headers
    my_headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': 'your_api_key_here',
        'X-Goog-FieldMask': 'routes.duration,routes.legs'
    }
    
    # Call Google Routes API
    api_url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    response = requests.post(api_url, json=my_body, headers=my_headers)
    print("API Response:", response.text)
    
    # Extract route steps and generate simulation data
    steps = response.json()["routes"][0]["legs"][0]["steps"]
    return generate_positions_speeds(steps)

def generate_positions_speeds(steps):
    """
    Process route steps to generate position and speed data
    Args:
        steps: List of route steps from Google Routes API
    Returns:
        Tuple of (positions_to_simulate, speeds_to_simulate)
    """
    positions_to_simulate = []
    speeds_to_simulate = []
    
    # Process each step in the route
    for step in steps:
        step_distance = step["distanceMeters"]
        step_time = float(step["staticDuration"].replace('s', ''))
        step_speed = step_distance / step_time
        
        # Decode polyline to get detailed path points
        substeps = decode_polyline(step["polyline"]["encodedPolyline"])
        
        # Process each segment between points
        for index in range(len(substeps) - 1):
            p1 = {"latitude": substeps[index][0], "longitude": substeps[index][1]}
            p2 = {"latitude": substeps[index + 1][0], "longitude": substeps[index + 1][1]}
            points_distance = distance(p1, p2) * 1000
            
            # Only process segments longer than 1 meter
            if points_distance > 1:
                sub_step_duration = points_distance / step_speed
                sub_step_speed = step_speed * 3.6  # Convert to km/h
                positions_to_simulate.append({
                    "Origin": p1,
                    "Destination": p2,
                    "Speed": sub_step_speed,
                    "Time": sub_step_duration
                })
                speeds_to_simulate.append({
                    "Speed": sub_step_speed,
                    "Time": sub_step_duration
                })
    
    return positions_to_simulate, speeds_to_simulate

def decode_polyline(polyline_str):
    """
    Decode Google's encoded polyline format
    Args:
        polyline_str: Encoded polyline string
    Returns:
        List of coordinate tuples (lat, lng)
    """
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'latitude': 0, 'longitude': 0}
    
    while index < len(polyline_str):
        for unit in ['latitude', 'longitude']:
            shift, result = 0, 0
            while not monitor.kill_now:
                byte = ord(polyline_str[index]) - 63
                index += 1
                result |= (byte & 0x1f) << shift
                shift += 5
                if not byte >= 0x20:
                    break
            changes[unit] = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += changes['latitude']
        lng += changes['longitude']
        coordinates.append((lat / 100000.0, lng / 100000.0))
    
    return coordinates

def distance(p1, p2):
    """
    Calculate great circle distance between two points
    Args:
        p1: First point {latitude, longitude}
        p2: Second point {latitude, longitude}
    Returns:
        Distance in kilometers
    """
    earth_radius = 6371.0087714
    result = earth_radius * acos(
        cos(radians(p1["latitude"])) * cos(radians(p2["latitude"])) *
        cos(radians(p2["longitude"]) - radians(p1["longitude"])) +
        sin(radians(p1["latitude"])) * sin(radians(p2["latitude"]))
    )
    return result

def send_positions_to_gps_simulator(positions_to_simulate):
    """
    Send position data to GPS simulator
    Args:
        positions_to_simulate: List of position data to send
    """
    GPS_SIMULATOR_HOST = os.getenv("GPS_SIMULATOR_HOST")
    GPS_SIMULATOR_PORT = int(os.getenv("GPS_SIMULATOR_PORT"))
    if GPS_SIMULATOR_PORT is None:
        raise ValueError("Missing environment variable: GPS_SIMULATOR_PORT")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((GPS_SIMULATOR_HOST, GPS_SIMULATOR_PORT))
        for position in positions_to_simulate:
            s.sendall(bytes(json.dumps(position), "utf-8"))
            data = s.recv(1024)
            print(f"{datetime.datetime.now()} - Sent position: {json.dumps(position)}")
            time.sleep(position["Time"])

def send_speeds_to_odometer_simulator(speeds_to_simulate):
    """
    Send speed data to odometer simulator
    Args:
        speeds_to_simulate: List of speed data to send
    """
    ODOMETER_SIMULATOR_HOST = os.getenv("ODOMETER_SIMULATOR_HOST")
    ODOMETER_SIMULATOR_PORT = int(os.getenv("ODOMETER_SIMULATOR_PORT"))
    if ODOMETER_SIMULATOR_PORT is None:
        raise ValueError("Missing environment variable: ODOMETER_SIMULATOR_PORT")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((ODOMETER_SIMULATOR_HOST, ODOMETER_SIMULATOR_PORT))
        for speed in speeds_to_simulate:
            s.sendall(bytes(json.dumps(speed), "utf-8"))
            data = s.recv(1024)
            print(f"{datetime.datetime.now()} - Sent speed: {json.dumps(speed)}")
            time.sleep(speed["Time"])

# Main execution block
if __name__ == '__main__':
    try:
        # Define route endpoints
        my_route = {"Origin": "Ayuntamiento de Leganés", "Destination": "Ayuntamiento de Getafe"}
        
        # Generate simulation data
        positions_to_simulate, speeds_to_simulate = generate_route_simulations(
            my_route["Origin"], 
            my_route["Destination"]
        )
        
        # Create and start simulation threads
        t1 = threading.Thread(target=send_positions_to_gps_simulator, 
                            args=(positions_to_simulate,), 
                            daemon=True)
        t2 = threading.Thread(target=send_speeds_to_odometer_simulator, 
                            args=(speeds_to_simulate,), 
                            daemon=True)
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        print(e)
