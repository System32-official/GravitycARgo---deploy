# GravitycARgo Route Planner

An advanced route planning application that provides optimized routes with weather forecasts and container recommendations for logistics operations.

## Features

- Multi-waypoint route planning
- Weather forecasting for route checkpoints
- Container recommendations based on weather conditions
- Interactive map visualization
- Alternative route suggestions
- Optimal checkpoint calculations
- Real-time weather monitoring

## Prerequisites

- Python 3.8+
- Flask web framework
- Modern web browser
- Internet connection for maps and weather data

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd GravityCARgo-/OptiGeniX\ mark\ 2/routing
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install required packages:

```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the Flask server:

```bash
python Server.py
```

2. Open your web browser and navigate to:

```
http://localhost:5001
```

## Project Structure

```
routing/
├── Server.py                    # Main Flask application server
├── route_checkpoints.py         # Route checkpoint calculation logic
├── osrm_services_demo.py        # OSRM routing services interface
├── weather_service.py           # Weather data integration
├── requirements.txt             # Python dependencies
├── static/
│   ├── css/                    # Stylesheets
│   └── js/                     # JavaScript files
└── templates/
    └── index.html              # Main application template
```

## API Endpoints

### 1. Calculate Route (`POST /calculate_route`)

Calculates optimal route with weather information.

Example request:

```json
{
  "source": "New York",
  "source_coords": [40.7128, -74.006],
  "destinations": [
    {
      "name": "Boston",
      "coords": [42.3601, -71.0589]
    }
  ],
  "checkpoints": 5,
  "start_time": "2024-01-20T10:00:00"
}
```

### 2. Search Location (`GET /search_location`)

Searches for locations using OpenStreetMap's Nominatim service.

Example:

```
GET /search_location?q=London
```

## Core Components

### 1. Route Planning

- Uses OSRM (Open Source Routing Machine) for route calculations
- Supports multiple destinations
- Provides alternative routes
- Calculates optimal checkpoints based on distance

### 2. Weather Integration

- Real-time weather data for each checkpoint
- Weather forecasting for estimated arrival times
- Route weather summary
- Temperature-based container recommendations

### 3. User Interface

- Interactive map visualization
- Dynamic route display
- Weather information panels
- Checkpoint navigation
- Container recommendations

## Configuration

The application uses several external services:

- OSRM for routing (default: router.project-osrm.org)
- OpenMeteo for weather data
- Nominatim for geocoding

## Development

To contribute or modify:

1. Main application logic is in `Server.py`
2. Weather service integration in `weather_service.py`
3. Route calculation logic in `route_checkpoints.py`
4. Frontend JavaScript in `static/js/main.js`
5. Styles in `static/css/style.css`

## Usage Example

1. Open the application in your browser
2. Enter source location (e.g., "New York")
3. Add one or more destinations
4. Set journey start time
5. Choose number of checkpoints or use optimal calculation
6. Click "Calculate Route"
7. View route details, weather information, and container recommendations

## Troubleshooting

Common issues:

1. If the map doesn't load:

   - Check internet connection
   - Ensure JavaScript is enabled
   - Clear browser cache

2. If weather data is unavailable:

   - Check OpenMeteo API status
   - Verify coordinates are valid

3. If route calculation fails:
   - Ensure OSRM service is accessible
   - Verify input coordinates
   - Check for valid start time

