import requests
from typing import List, Tuple, Optional, Dict
from tenacity import retry, stop_after_attempt, wait_exponential, before_log, after_log
import polyline
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)  # Change DEBUG to INFO
logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    before=before_log(logger, logging.DEBUG),
    after=before_log(logger, logging.DEBUG)
)
def _fetch_osrm_route(source: Tuple[float, float], destination: Tuple[float, float]) -> Optional[dict]:
    """Fetch route from OSRM with retry logic."""
    try:
        base_url = "http://router.project-osrm.org/route/v1/driving"
        url = f"{base_url}/{source[1]},{source[0]};{destination[1]},{destination[0]}"
        params = {"overview": "full", "geometries": "polyline"}
        
        logger.debug(f"Requesting route from OSRM: {url}")
        response = requests.get(url, params=params, timeout=10)  # Add timeout
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching route: {str(e)}")
        raise

def _extract_checkpoints(route_geometry: str, num_checkpoints: int) -> List[Tuple[float, float]]:
    """Extract evenly spaced checkpoints from route geometry."""
    # Decode the polyline to get all route points
    route_points = polyline.decode(route_geometry)
    
    if not route_points:
        return []
    
    # Include source and destination
    checkpoints = [route_points[0]]
    
    if num_checkpoints > 2:
        # Calculate spacing between points
        total_points = len(route_points)
        spacing = total_points / (num_checkpoints - 1)
        
        # Extract intermediate checkpoints
        for i in range(1, num_checkpoints - 1):
            index = int(i * spacing)
            if index < total_points:
                checkpoints.append(route_points[index])
    
    # Add destination
    checkpoints.append(route_points[-1])
    return checkpoints

def reverse_geocode(lat: float, lon: float) -> str:
    """Get location name from coordinates using Nominatim API"""
    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 12  # Use zoom level 12 for district/suburb precision
        }
        headers = {
            "User-Agent": "GravityCARgo Route Planner"
        }
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Extract the most relevant name from the address
        address = data.get('address', {})
        location_name = (
            address.get('suburb') or 
            address.get('town') or 
            address.get('city') or 
            address.get('village') or 
            address.get('district') or 
            "Unknown Location"
        )
        return location_name
    
    except Exception as e:
        logger.error(f"Error reverse geocoding: {str(e)}")
        return "Unknown Location"

def calculate_optimal_checkpoints(distance_km: float) -> int:
    """Calculate optimal number of checkpoints based on route distance"""
    if distance_km <= 50:  # Short route
        return 2  # Just source and destination
    elif distance_km <= 100:
        return 3  # One checkpoint in middle
    elif distance_km <= 200:
        return 4
    elif distance_km <= 500:
        return 6
    else:
        return 8  # Maximum checkpoints for long routes

def fetch_route_checkpoints(source: Tuple[float, float], destination: Tuple[float, float], num_checkpoints: int = None) -> List[Dict]:
    """Enhanced function to return checkpoints with location names"""
    # Get route first to calculate distance
    route_data = _fetch_osrm_route(source, destination)
    if not route_data or "routes" not in route_data:
        raise ValueError("Could not fetch route")
    
    # Calculate distance in kilometers
    distance_km = route_data['routes'][0]['distance'] / 1000
    
    # If num_checkpoints not specified, calculate optimal number
    if num_checkpoints is None:
        num_checkpoints = calculate_optimal_checkpoints(distance_km)
    
    # Get checkpoint coordinates
    checkpoint_coords = _extract_checkpoints(route_data['routes'][0]['geometry'], num_checkpoints)
    
    # Create checkpoint info with names
    checkpoints = []
    for i, coords in enumerate(checkpoint_coords):
        name = reverse_geocode(coords[0], coords[1])
        checkpoints.append({
            'index': i,
            'name': name,
            'coords': coords,
            'distance_from_start': (distance_km * i / (num_checkpoints - 1)) if i > 0 else 0
        })
    
    return checkpoints

def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate latitude and longitude values."""
    return -90 <= lat <= 90 and -180 <= lon <= 180

def geocode_location(location_name: str) -> Tuple[float, float]:
    """Convert location name to coordinates using Nominatim API."""
    try:
        # Using Nominatim API
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": location_name,
            "format": "json",
            "limit": 1
        }
        headers = {
            "User-Agent": "GravityCARgo Route Planner"
        }
        
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            raise ValueError(f"Location not found: {location_name}")
        
        location = data[0]
        return (float(location["lat"]), float(location["lon"]))
    
    except Exception as e:
        logger.error(f"Error geocoding location: {str(e)}")
        raise

def get_location_input(prompt: str) -> Tuple[str, Tuple[float, float]]:
    """Get location input from user and convert to coordinates."""
    while True:
        try:
            location_name = input(prompt).strip()
            if not location_name:
                print("Please enter a location name!")
                continue
                
            print(f"Looking up coordinates for {location_name}...")
            coords = geocode_location(location_name)
            return (location_name, coords)
            
        except ValueError as e:
            print(f"Error: {str(e)}")
        except Exception as e:
            print("Error looking up location. Please try again.")

if __name__ == "__main__":
    try:
        print("=== Route Checkpoint Generator ===")
        
        # Get source location
        source_name, source_coords = get_location_input("\nEnter source location (e.g., 'New York'): ")
        print(f"Found coordinates: {source_coords[0]:.5f}, {source_coords[1]:.5f}")
        
        # Get destination location
        dest_name, dest_coords = get_location_input("\nEnter destination location (e.g., 'Los Angeles'): ")
        print(f"Found coordinates: {dest_coords[0]:.5f}, {dest_coords[1]:.5f}")
        
        # Get number of checkpoints
        while True:
            try:
                num_points = int(input("\nNumber of checkpoints (minimum 2): "))
                if num_points >= 2:
                    break
                print("Please enter a number >= 2")
            except ValueError:
                print("Please enter a valid number!")
        
        logger.info("Fetching route checkpoints...")
        checkpoints = fetch_route_checkpoints(source_coords, dest_coords, num_checkpoints=num_points)
        
        print(f"\nRoute from {source_name} to {dest_name}:")
        print("-" * 40)
        print(f"Start: {source_name} ({checkpoints[0]['coords'][0]:.5f}, {checkpoints[0]['coords'][1]:.5f}) - {checkpoints[0]['name']}")
        
        # Print intermediate points
        for i, checkpoint in enumerate(checkpoints[1:-1], 1):
            print(f"Checkpoint {i}: ({checkpoint['coords'][0]:.5f}, {checkpoint['coords'][1]:.5f}) - {checkpoint['name']}")
            
        print(f"End: {dest_name} ({checkpoints[-1]['coords'][0]:.5f}, {checkpoints[-1]['coords'][1]:.5f}) - {checkpoints[-1]['name']}")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)
