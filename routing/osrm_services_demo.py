import requests
from typing import List, Dict, Any, Union, Tuple
import logging

logger = logging.getLogger(__name__)

class OSRMServices:
    """Interface for OSRM (Open Source Routing Machine) services"""
    
    def __init__(self, base_url: str = "http://router.project-osrm.org"):
        self.base_url = base_url.rstrip('/')
        
    def route(self, coordinates: List[Tuple[float, float]], alternatives: bool = False) -> Dict[str, Any]:
        """Get route between coordinates"""
        try:
            # OSRM expects coordinates as lon,lat
            coords_str = ';'.join([f"{lon},{lat}" for lat, lon in coordinates])
            url = f"{self.base_url}/route/v1/driving/{coords_str}"
            
            params = {
                "alternatives": str(alternatives).lower(),
                "steps": "true",
                "annotations": "true",
                "geometries": "polyline",
                "overview": "full"
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 'Ok':
                logger.error(f"OSRM route error: {data.get('message', 'Unknown error')}")
                raise ValueError(data.get('message', 'Route calculation failed'))
                
            return data
                
        except Exception as e:
            logger.error(f"Route request failed: {str(e)}")
            raise
            
    def nearest(self, coordinates: List[Tuple[float, float]], number: int = 1) -> Dict[str, Any]:
        """Find nearest road segments to coordinates"""
        coords_str = ';'.join([f"{lon},{lat}" for lat, lon in coordinates])
        url = f"{self.base_url}/nearest/v1/driving/{coords_str}"
        
        params = {
            "number": number
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Nearest request failed: {str(e)}")
            raise
            
    def table(self, coordinates: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Generate duration/distance matrix between coordinates"""
        coords_str = ';'.join([f"{lon},{lat}" for lat, lon in coordinates])
        url = f"{self.base_url}/table/v1/driving/{coords_str}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Table request failed: {str(e)}")
            raise
            
    def trip(self, coordinates: List[Tuple[float, float]]) -> Dict[str, Any]:
        """Solve Traveling Salesperson Problem for coordinates"""
        coords_str = ';'.join([f"{lon},{lat}" for lat, lon in coordinates])
        url = f"{self.base_url}/trip/v1/driving/{coords_str}"
        
        params = {
            "steps": "true",
            "geometries": "polyline",
            "overview": "full"
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Trip request failed: {str(e)}")
            raise
