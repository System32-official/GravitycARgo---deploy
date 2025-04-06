"""Constants for the container packing system"""

# Container dimensions (Length, Width, Height) in meters and Maximum Payload Weight in kg
CONTAINER_TYPES = {
    # Standard Containers
    'Twenty-foot': (5.90, 2.35, 2.39, 28180),  # Added max payload weight
    'Forty-foot': (12.00, 2.35, 2.39, 28800),  # Added max payload weight
    'Forty-foot-HC': (12.00, 2.35, 2.69, 28560),  # Added max payload weight
    'Forty-five-foot-HC': (13.55, 2.35, 2.69, 27600),  # Added max payload weight
    
    # Refrigerated Containers
    'Reefer-20ft': (5.44, 2.29, 2.27, 27700),  # Added max payload weight
    'Reefer-40ft': (11.56, 2.29, 2.27, 29000),  # Added max payload weight
    
    # Open Top Containers
    'Open-Top-20ft': (5.90, 2.35, 2.39, 28180),  # Added max payload weight
    'Open-Top-40ft': (12.00, 2.35, 2.39, 27700),  # Added max payload weight
    
    # Flat Rack Containers
    'Flat-Rack-20ft': (6.06, 2.44, 2.44, 27940),  # Added max payload weight
    'Flat-Rack-40ft': (12.19, 2.44, 2.44, 39340)  # Added max payload weight
}

# Transport modes with their available container types
TRANSPORT_MODES = {
    '1': ('Road Transport', [
        'Twenty-foot', 'Forty-foot', 'Forty-foot-HC',
        'Reefer-20ft', 'Reefer-40ft'
    ]),
    '2': ('Rail Transport', [
        'Twenty-foot', 'Forty-foot', 'Forty-foot-HC',
        'Flat-Rack-20ft', 'Flat-Rack-40ft'
    ]),
    '3': ('Air Transport', [
        'Twenty-foot', 'Reefer-20ft'  # Limited to smaller containers for air transport
    ]),
    '4': ('Maritime Transport', [
        'Twenty-foot', 'Forty-foot', 'Forty-foot-HC', 'Forty-five-foot-HC',
        'Reefer-20ft', 'Reefer-40ft', 'Open-Top-20ft', 'Open-Top-40ft',
        'Flat-Rack-20ft', 'Flat-Rack-40ft'
    ]),
    '5': ('Inland Waterways', [
        'Twenty-foot', 'Forty-foot',
        'Open-Top-20ft', 'Open-Top-40ft'
    ])
}
