"""
EnhancedContainer class with advanced packing algorithms
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
import random
from datetime import datetime
import json
from typing import List, Tuple, Dict
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

from optigenix_module.models.item import Item
from optigenix_module.models.space import MaximalSpace
from optigenix_module.models.container_core import ContainerCore
from optigenix_module.models.container_metrics import ContainerMetrics
from optigenix_module.models.container_packing import ContainerPacking
from optigenix_module.models.container_visualization import ContainerVisualization
from optigenix_module.models.container_reporting import ContainerReporting

class EnhancedContainer(ContainerCore, ContainerMetrics, ContainerPacking, 
                        ContainerVisualization, ContainerReporting):
    """
    Enhanced container class that combines functionality from multiple modules
    
    This class integrates core container functionality, metrics calculations,
    packing algorithms, visualization tools, and reporting capabilities.
    """
    
    def __init__(self, dimensions, route_temperature=None):
        """Initialize container with specified dimensions and optional route temperature"""
        # Validate dimensions
        if not all(isinstance(d, (int, float)) and d > 0 for d in dimensions):
            raise ValueError("Container dimensions must be positive numbers")
        if len(dimensions) != 3:
            raise ValueError("Container must have exactly 3 dimensions (length, width, height)")
            
        self.dimensions = tuple(float(d) for d in dimensions)
        self.items = []
        
        # Store route temperature for temperature-sensitive item handling
        self.route_temperature = route_temperature
        
        # Create completely separate space systems for temperature-sensitive and normal items
        wall_buffer = 0.1  # 10cm buffer from walls
        
        # 1. Standard space - for regular items (includes positions near walls)
        standard_space = MaximalSpace(0, 0, 0, dimensions[0], dimensions[1], dimensions[2])
        standard_space.temperature_safe = False
        
        # 2. Temperature-safe space - with buffer from all walls
        # This is used exclusively for temperature-sensitive items
        temp_safe_space = MaximalSpace(
            wall_buffer,                         # x with buffer from left wall
            wall_buffer,                         # y with buffer from front wall
            0,                                   # z starts at bottom
            dimensions[0] - (2 * wall_buffer),   # width with buffer from both sides
            dimensions[1] - (2 * wall_buffer),   # depth with buffer from front/back
            dimensions[2] - wall_buffer          # height with buffer from top
        )
        temp_safe_space.temperature_safe = True
        
        # Initialize with both spaces - they'll be kept separate throughout packing
        self.spaces = [standard_space, temp_safe_space]
        
        # Initialize other container properties
        self.weight_distribution = {}
        self.volume_utilization = 0.0
        self.layer_height = 0
        self.weight_map = np.zeros((10, 10))  # Grid for weight distribution
        self.center_of_gravity = [0, 0, 0]
        self.unpacked_reasons = {}
        self.total_weight = 0
        self.unused_spaces = []  # Track remaining spaces
        self.unpacked_reasons = {}  # Enhanced reasons tracking
        self.total_volume = dimensions[0] * dimensions[1] * dimensions[2]
        self.remaining_volume = self.total_volume
        self.support_mechanisms = []  # Track support mechanisms used
        
        if route_temperature is not None:
            print(f"\n🌡️ CONTAINER INITIALIZED WITH TEMPERATURE SYSTEM")
            print(f"   Route temperature: {route_temperature}°C")
            print(f"   Temperature-sensitive items will use temperature-safe spaces")
            print(f"   Wall buffer: {wall_buffer*100:.1f}cm from all container walls")
            print(f"   Available space for temperature-sensitive items: {temp_safe_space.width:.2f}m × {temp_safe_space.depth:.2f}m × {temp_safe_space.height:.2f}m\n")

    # generate_alternative_arrangement method removed