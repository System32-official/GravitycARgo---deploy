from flask import Flask, render_template, jsonify, request
from .route_checkpoints import fetch_route_checkpoints, geocode_location
from .osrm_services_demo import OSRMServices
from .weather_service import WeatherService
import json
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
osrm = OSRMServices()
weather_service = WeatherService()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate_route', methods=['POST'])
def calculate_route():
    try:
        data = request.json
        source_name = data['source']
        source_coords = tuple(data['source_coords'])  # Already as [lat, lon]
        destinations = data['destinations']  # List of destinations with name and coords
        num_checkpoints = data.get('checkpoints', None)

        # Validate coordinates
        if not (-90 <= source_coords[0] <= 90 and -180 <= source_coords[1] <= 180):
            raise ValueError("Invalid source coordinates")
        
        for dest in destinations:
            dest_coords = dest['coords']
            if not (-90 <= dest_coords[0] <= 90 and -180 <= dest_coords[1] <= 180):
                raise ValueError(f"Invalid coordinates for destination {dest['name']}")
        
        # Create waypoints list with source first, then all destinations
        waypoints = [source_coords]
        for dest in destinations:
            waypoints.append(tuple(dest['coords']))
        
        # Calculate multi-waypoint route
        route_data = osrm.route(waypoints)
        
        if route_data.get('code') != 'Ok':
            raise ValueError("Could not find route between locations")
        
        # Calculate total distance and duration
        total_distance_km = route_data['routes'][0]['distance'] / 1000
        total_duration_hours = route_data['routes'][0]['duration'] / 3600
        
        # Get checkpoints between each segment
        all_checkpoints = []
        segment_checkpoints = {}
        
        # Calculate checkpoints between each consecutive pair of waypoints
        for i in range(len(waypoints) - 1):
            source_segment = waypoints[i]
            dest_segment = waypoints[i+1]
            
            # Either use specified number or calculate based on segment distance
            segment_route = osrm.route([source_segment, dest_segment])
            segment_distance = segment_route['routes'][0]['distance'] / 1000
            
            # Calculate number of checkpoints for this segment if optimal
            if num_checkpoints is None:
                # Determine number of checkpoints based on segment distance
                segment_checkpoints = max(2, int(segment_distance / 100) + 2)
            else:
                # Distribute checkpoints proportionally among segments
                segment_checkpoints = max(2, int(num_checkpoints * segment_distance / total_distance_km))
            
            # Get checkpoints for this segment
            checkpoints = fetch_route_checkpoints(source_segment, dest_segment, segment_checkpoints)
            
            # For non-first segments, remove the first checkpoint as it's duplicate
            if i > 0 and checkpoints:
                checkpoints = checkpoints[1:]
                
            all_checkpoints.extend(checkpoints)
        
        # Get alternative routes - only for full route
        alt_routes = osrm.route(waypoints, alternatives=True)
        
        # Enhance route data with step information
        for route in [route_data['routes'][0]] + alt_routes.get('routes', [])[1:]:
            for leg in route['legs']:
                for step in leg['steps']:
                    # Add road type classification
                    if 'motorway' in step.get('ref', '').lower():
                        step['road_type'] = 'highway'
                    elif any(x in step.get('ref', '').lower() for x in ['trunk', 'primary']):
                        step['road_type'] = 'major'
                    else:
                        step['road_type'] = 'local'
        
        # Get start time
        start_time = data.get('start_time', None)
        if not start_time:
            raise ValueError("Start time is required")
        
        # Calculate weather for route based on checkpoints
        weather_summary = weather_service.get_route_weather_summary(
            all_checkpoints,
            total_duration_hours
        )
        
        # Get container recommendations
        container_recommendations = weather_service.get_container_recommendations(
            weather_summary['avg_temperature']
        )
        
        # Calculate checkpoint arrival times and weather
        checkpoint_details = []
        start_time_dt = datetime.fromisoformat(data['start_time'])
        
        total_distance_so_far = 0
        total_duration_so_far = 0
        
        # Process weather for each checkpoint
        for idx, checkpoint in enumerate(all_checkpoints):
            # For first checkpoint (source), time is the start time
            if idx == 0:
                arrival_time = start_time_dt
                hours_from_start = 0
            else:
                # Estimate time proportionally along the route
                # Assuming constant speed, calculate progress through route
                progress = total_distance_so_far / total_distance_km
                hours_from_start = total_duration_hours * progress
                arrival_time = start_time_dt + timedelta(hours=hours_from_start)
            
            # Update distance for next checkpoint
            if idx < len(all_checkpoints) - 1:
                segment_distance = osrm.route([
                    (checkpoint['coords'][0], checkpoint['coords'][1]),
                    (all_checkpoints[idx+1]['coords'][0], all_checkpoints[idx+1]['coords'][1])
                ])['routes'][0]['distance'] / 1000
                
                total_distance_so_far += segment_distance
            
            # Get current weather
            current_weather = weather_service.get_current_weather(
                checkpoint['coords'][0],
                checkpoint['coords'][1]
            )
            
            # Get forecast weather at arrival
            forecast_weather = weather_service.get_checkpoint_weather(
                checkpoint['coords'][0],
                checkpoint['coords'][1],
                hours_from_start
            )
            
            checkpoint_details.append({
                **checkpoint,
                'arrival_time': arrival_time.isoformat(),
                'hours_from_start': hours_from_start,
                'current_weather': current_weather,
                'forecast_weather': forecast_weather
            })
        
        # Create a list of destination names for display
        destination_names = [dest['name'] for dest in destinations]
        
        return jsonify({
            'status': 'success',
            'main_route': route_data['routes'][0],
            'alternative_routes': alt_routes.get('routes', [])[1:] if alt_routes.get('code') == 'Ok' else [],
            'checkpoints': checkpoint_details,
            'route_info': {
                'distance_km': total_distance_km,
                'duration_hours': total_duration_hours,
                'optimal_stops': len(all_checkpoints),
                'weather_summary': weather_summary,
                'container_recommendations': container_recommendations,
                'start_time': start_time_dt.isoformat(),
                'multi_destination': True,
                'waypoint_count': len(waypoints)
            },
            'source': {'name': source_name, 'coords': source_coords},
            'destinations': destinations
        })

    except Exception as e:
        print(f"Route calculation error: {str(e)}")  # For debugging
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/search_location', methods=['GET'])
def search_location():
    query = request.args.get('q', '')
    if len(query) < 3:
        return jsonify({'locations': []})
    
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": query,
            "format": "json",
            "limit": 5,
            "addressdetails": 1
        }
        headers = {
            "User-Agent": "GravityCARgo Route Planner"
        }
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        locations = [{
            'lat': float(loc['lat']),
            'lon': float(loc['lon']),
            'display_name': loc['display_name']
        } for loc in response.json()]
        
        return jsonify({'locations': locations})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5001)
