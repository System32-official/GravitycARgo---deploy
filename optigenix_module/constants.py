"""Constants for the container packing system"""

# Container dimensions (Length, Width, Height) in meters and Maximum Payload Weight in kg
CONTAINER_TYPES = {
    # Standard Containers
    'Twenty-foot': (5.90, 2.35, 2.39, 28180),  # Added max payload weight
    'Forty-foot': (12.00, 2.35, 2.39, 28800),  # Added max payload weight
    'Forty-foot-HC': (12.00, 2.35, 2.69, 28560),  # Added max payload weight
    'Forty-five-foot-HC': (13.55, 2.35, 2.69, 27600),  # Added max payload weight
    
    # Refrigerated Containers
    'Reefer-20ft': (5.44, 2.29, 2.27, 27700),  # Added max payload weight for temperature control
    'Reefer-40ft': (11.56, 2.29, 2.27, 29000),  # Added max payload weight for temperature control
    
    # Open Top Containers
    'Open-Top-20ft': (5.90, 2.35, 2.39, 28180),  # Added max payload weight
    'Open-Top-40ft': (12.00, 2.35, 2.39, 27700),  # Added max payload weight
    
    # Flat Rack Containers 
    'Flat-Rack-20ft': (6.06, 2.44, 2.44, 27940),  # Added max payload weight
    'Flat-Rack-40ft': (12.19, 2.44, 2.44, 39340), # Added max payload weight
}

# Transport modes with their available container types
TRANSPORT_MODES = {
    '1': ('Road Transport', [
        'Twenty-foot', 'Forty-foot', 'Forty-foot-HC',
        'Reefer-20ft', 'Reefer-40ft', 'Open-Top-20ft', 'Open-Top-40ft',
        'Flat-Rack-20ft', 'Flat-Rack-40ft'
    ]),
    '2': ('Sea Transport', [
        'Twenty-foot', 'Forty-foot', 'Forty-foot-HC', 'Forty-five-foot-HC',
        'Reefer-20ft', 'Reefer-40ft', 'Open-Top-20ft', 'Open-Top-40ft',
        'Flat-Rack-20ft', 'Flat-Rack-40ft'
    ]),
    '3': ('Air Transport', [
        'Twenty-foot', 'Reefer-20ft'  # Limited to smaller containers for air transport
    ]),
    '4': ('Rail Transport', [
        'Twenty-foot', 'Forty-foot', 'Forty-foot-HC',
        'Flat-Rack-20ft', 'Flat-Rack-40ft'
    ]),
    '5': ('Custom', [])  # No predefined containers for custom
}

# Container type definitions
CONTAINER_TYPES_DETAILED = {
    'Twenty-foot': {
        'dimensions': [5.9, 2.35, 2.39],
        'max_weight': 28230,
        'description': '20ft Standard Container'
    },
    'Forty-foot': {
        'dimensions': [12.03, 2.35, 2.39],
        'max_weight': 30480,
        'description': '40ft Standard Container'
    },
    'Forty-foot-HC': {
        'dimensions': [12.03, 2.35, 2.69],
        'max_weight': 30480,
        'description': '40ft High Cube Container'
    },
    'Open-Top-20ft': {
        'dimensions': [5.9, 2.35, 2.39],
        'max_weight': 28230,
        'description': '20ft Open Top Container'
    },
    'Open-Top-40ft': {
        'dimensions': [12.03, 2.35, 2.39],
        'max_weight': 30480,
        'description': '40ft Open Top Container'
    }
}

# Transport mode definitions
TRANSPORT_MODES_LIST = [
    'Road Transport',
    'Rail Transport',
    'Sea Transport',
    'Air Transport',
    'Multimodal Transport'
]

# Temperature ranges for different transport modes
TRANSPORT_TEMPERATURE_RANGES = {
    'Road Transport': {'min': -20, 'max': 50},
    'Rail Transport': {'min': -25, 'max': 45},
    'Sea Transport': {'min': -30, 'max': 60},
    'Air Transport': {'min': -40, 'max': 70},
    'Multimodal Transport': {'min': -30, 'max': 60}
}

# Fragility levels
FRAGILITY_LEVELS = ['LOW', 'MEDIUM', 'HIGH']

# Boxing types
BOXING_TYPES = ['BOX', 'PALLET', 'CRATE', 'DRUM', 'FRAME', 'CARTON']

# Stackable options
STACKABLE_OPTIONS = ['YES', 'NO']

# Bundle options
BUNDLE_OPTIONS = ['YES', 'NO']

def get_predefined_container_dimensions(container_name: str):
    """Retrieve predefined container dimensions by name."""
    container_info = CONTAINER_TYPES_DETAILED.get(container_name)
    if container_info:
        return container_info.get('dimensions')
    # Fallback to CONTAINER_TYPES if not in DETAILED, and extract only dimensions
    container_fallback_info = CONTAINER_TYPES.get(container_name)
    if container_fallback_info:
        return list(container_fallback_info[:3]) # Return L, W, H as a list
    return None # Or raise an error if the container name is not found
