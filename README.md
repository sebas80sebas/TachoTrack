# TachoTrack - Digital Tachograph Simulation System

## Project Structure

This project simulates a digital tachograph system with cloud integration through two main components:

### 1. Virtual Tachograph (`/VirtualTachograph`)

Simulates tachograph hardware with:
- Control Unit 
- Card Reader
- GPS/GNSS
- Odometer
- Routes Generator

### 2. IoT Cloud Services (`/IoTCloudServices`)

Cloud infrastructure including:
- Message Router (MQTT)
- Microservices:
  - Devices
  - Sessions 
  - Telemetry
  - Events
- Web Application:
  - Frontend UI
  - Backend API
- Database (MariaDB)

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Mosquitto MQTT client (for testing)

### Running the System

1. Start Cloud Services:
```bash
cd IoTCloudServices
./cloud.sh
```

2. Launch Virtual Tachograph:
```bash
cd VirtualTachograph
docker compose up -d
```

3. Access web interface:
```
http://localhost
```

## Testing

### MQTT Testing
```bash
# Subscribe to all topics
mosquitto_sub -h localhost -t "#" -v -u fic_server -P fic_password

# Publish test message
mosquitto_pub -h localhost -t "fic/tachographs/tachograph_control_unit-1/request_access/" \
  -m '{"tachograph_id": "tachograph_control_unit-1"}' \
  -u fic_server -P fic_password
```

### API Testing
```bash
# Get active tachographs
curl http://localhost:5001/tachographs/

# Register new tachograph
curl -X POST http://localhost:5001/tachographs/ \
  -H "Content-Type: application/json" \
  -d '{"tachograph_id": "tachograph_control_unit-1"}'
```

## Architecture

- Docker containerization
- MQTT messaging protocol 
- REST APIs
- MariaDB database
- Web-based visualization

## License

This project is licensed under the MIT License.
