import requests
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

class WeatherService:
    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1/forecast"

    def get_current_weather(self, lat: float, lon: float) -> Dict:
        """Get current weather conditions"""
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation_probability"]
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            current = data["current_weather"]
            return {
                "temperature": current["temperature"],
                "time": current["time"],
                "humidity": data["hourly"]["relative_humidity_2m"][0],
                "precipitation_prob": data["hourly"]["precipitation_probability"][0]
            }
        except Exception as e:
            print(f"Current weather error: {str(e)}")
            return None

    def get_checkpoint_weather(self, lat: float, lon: float, hours_from_start: float) -> Dict:
        """Get weather forecast for checkpoint at estimated arrival time"""
        try:
            # Calculate when we'll arrive at this checkpoint
            forecast_time = datetime.now() + timedelta(hours=hours_from_start)
            
            # Get weather forecast for that day
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation_probability"],
                "start_date": forecast_time.strftime("%Y-%m-%d"),
                "end_date": (forecast_time + timedelta(days=1)).strftime("%Y-%m-%d")
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Get forecast for specific hour of arrival
            target_hour = forecast_time.hour
            return {
                "temperature": data["hourly"]["temperature_2m"][target_hour],
                "humidity": data["hourly"]["relative_humidity_2m"][target_hour],
                "precipitation_prob": data["hourly"]["precipitation_probability"][target_hour],
                "forecast_time": forecast_time.strftime("%Y-%m-%d %H:00")
            }
            
        except Exception as e:
            print(f"Weather forecast error: {str(e)}")
            return None

    def get_route_weather_summary(self, checkpoints: List[Dict], route_duration: float) -> Dict:
        """Calculate weather summary for entire route"""
        total_temp = 0
        temps = []
        humidity = []
        precipitation = []
        
        for idx, checkpoint in enumerate(checkpoints):
            # Calculate when we'll reach this checkpoint
            progress = idx / (len(checkpoints) - 1)
            hours_from_start = route_duration * progress
            
            weather = self.get_checkpoint_weather(
                checkpoint['coords'][0],
                checkpoint['coords'][1],
                hours_from_start
            )
            
            if weather:
                temps.append(weather['temperature'])
                humidity.append(weather['humidity'])
                precipitation.append(weather['precipitation_prob'])
                total_temp += weather['temperature']
                
                # Add weather to checkpoint data
                checkpoint['weather'] = weather
        
        return {
            'avg_temperature': sum(temps) / len(temps) if temps else None,
            'min_temperature': min(temps) if temps else None,
            'max_temperature': max(temps) if temps else None,
            'avg_humidity': sum(humidity) / len(humidity) if humidity else None,
            'max_precipitation_prob': max(precipitation) if precipitation else None
        }

    def get_container_recommendations(self, avg_temp: float) -> Dict:
        """Get container recommendations based on average temperature"""
        if avg_temp < 0:
            return {
                "container_type": "Heated Container",
                "settings": "Maintain temperature above 5°C",
                "precautions": ["Use thermal blankets", "Install temperature monitoring"]
            }
        elif avg_temp < 15:
            return {
                "container_type": "Temperature Controlled",
                "settings": "Maintain 15-20°C",
                "precautions": ["Regular temperature checks", "Insulation recommended"]
            }
        elif avg_temp < 25:
            return {
                "container_type": "Standard Container",
                "settings": "Normal ventilation",
                "precautions": ["Basic weather protection"]
            }
        else:
            return {
                "container_type": "Refrigerated Container",
                "settings": "Maintain temperature below 25°C",
                "precautions": ["Active cooling", "Air circulation", "Sun protection"]
            }
