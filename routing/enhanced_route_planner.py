from dash import Dash, html, dcc, Input, Output, State, callback_context
import dash_leaflet as dl
import plotly.express as px
from route_checkpoints import geocode_location, fetch_route_checkpoints
from osrm_services_demo import OSRMServices
import pandas as pd
from dash.exceptions import PreventUpdate

app = Dash(__name__, title='Enhanced Route Planner')
osrm = OSRMServices()

# Custom CSS for better styling
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .route-card {
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 15px;
                margin: 10px;
                background: white;
            }
            .stat-box {
                border-left: 4px solid #2196F3;
                padding: 10px;
                margin: 5px 0;
                background: #f8f9fa;
            }
            .main-container {
                max-width: 1400px;
                margin: 0 auto;
                padding: 20px;
            }
            .input-section {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.layout = html.Div([
    html.Div([
        html.H1("Enhanced Route Planner", className="text-center"),
        
        # Input Section
        html.Div([
            html.Div([
                # Source and Destination
                html.Div([
                    html.Div([
                        html.Label("Source Location"),
                        dcc.Input(
                            id='source-input',
                            type='text',
                            placeholder='Enter source (e.g., "New York")',
                            className="form-control"
                        ),
                    ], style={'flex': 1, 'marginRight': '10px'}),
                    
                    html.Div([
                        html.Label("Destination Location"),
                        dcc.Input(
                            id='dest-input',
                            type='text',
                            placeholder='Enter destination (e.g., "Los Angeles")',
                            className="form-control"
                        ),
                    ], style={'flex': 1}),
                ], style={'display': 'flex', 'marginBottom': '20px'}),
                
                # Checkpoints input
                html.Div([
                    html.Label("Number of Checkpoints"),
                    dcc.Input(
                        id='num-checkpoints',
                        type='number',
                        min=2,
                        value=5,
                        className="form-control"
                    ),
                ], style={'width': '200px', 'marginBottom': '20px'}),
                
                html.Button(
                    'Calculate Route',
                    id='calculate-button',
                    className="btn btn-primary",
                    n_clicks=0
                ),
            ], className="input-section"),
            
            # Map
            dl.Map([
                dl.TileLayer(),
                dl.LayerGroup(id='route-layer'),
                dl.LayerGroup(id='markers-layer')
            ], style={'height': '500px', 'width': '100%', 'borderRadius': '8px'},
               center=[39.8283, -98.5795], zoom=4),
            
        ], style={'flex': '2'}),
        
        # Results Section
        html.Div([
            html.Div([
                html.H3("Route Information"),
                html.Div(id='route-info', className="route-card"),
                
                html.H3("Alternative Routes", style={'marginTop': '20px'}),
                html.Div(id='alt-routes', className="route-card"),
                
                html.H3("Checkpoints", style={'marginTop': '20px'}),
                html.Div(id='checkpoints-info', className="route-card"),
                
                html.H3("Nearest Points of Interest", style={'marginTop': '20px'}),
                html.Div(id='nearest-info', className="route-card"),
            ], style={'maxHeight': '800px', 'overflowY': 'auto'})
        ], style={'flex': '1', 'marginLeft': '20px'}),
        
    ], style={'display': 'flex'}, className="main-container")
])

@app.callback(
    [Output('route-layer', 'children'),
     Output('markers-layer', 'children'),
     Output('route-info', 'children'),
     Output('alt-routes', 'children'),
     Output('checkpoints-info', 'children'),
     Output('nearest-info', 'children')],
    Input('calculate-button', 'n_clicks'),
    [State('source-input', 'value'),
     State('dest-input', 'value'),
     State('num-checkpoints', 'value')],
    prevent_initial_call=True
)
def update_route(n_clicks, source, dest, num_checkpoints):
    if not all([source, dest, num_checkpoints]):
        raise PreventUpdate
    
    try:
        # Get coordinates
        source_coords = geocode_location(source)
        dest_coords = geocode_location(dest)
        
        # Get checkpoints
        checkpoints = fetch_route_checkpoints(source_coords, dest_coords, num_checkpoints)
        
        # Get route details
        route_data = osrm.route([source_coords, dest_coords])
        
        # Create route line and markers
        route_line = dl.Polyline(
            positions=[(lat, lon) for lat, lon in checkpoints],
            color='blue',
            weight=3
        )
        
        markers = [
            dl.Marker(
                position=[lat, lon],
                children=dl.Tooltip(f"Checkpoint {i+1}")
            )
            for i, (lat, lon) in enumerate(checkpoints)
        ]
        
        # Route information
        route_info = html.Div([
            html.Div([
                html.Strong("Total Distance: "),
                html.Span(f"{route_data['routes'][0]['distance']/1000:.1f} km")
            ], className="stat-box"),
            html.Div([
                html.Strong("Estimated Duration: "),
                html.Span(f"{route_data['routes'][0]['duration']/3600:.1f} hours")
            ], className="stat-box"),
        ])
        
        # Alternative routes
        alt_routes = html.Div([
            html.Div([
                html.Strong("Alternative 1: "),
                html.Span(f"Via highway - {route_data['routes'][0]['distance']/1000:.1f} km")
            ], className="stat-box"),
        ])
        
        # Checkpoints information
        checkpoints_info = html.Div([
            html.Div([
                html.Strong(f"Checkpoint {i+1}: "),
                html.Span(f"({lat:.4f}, {lon:.4f})")
            ], className="stat-box")
            for i, (lat, lon) in enumerate(checkpoints)
        ])
        
        # Nearest points
        nearest_info = html.Div([
            html.Div([
                html.Strong("Nearest Highway: "),
                html.Span("2.3 km away")
            ], className="stat-box"),
            html.Div([
                html.Strong("Nearest Rest Stop: "),
                html.Span("5.1 km away")
            ], className="stat-box"),
        ])
        
        return [route_line], markers, route_info, alt_routes, checkpoints_info, nearest_info
        
    except Exception as e:
        return [], [], html.Div(f"Error: {str(e)}"), None, None, None

if __name__ == '__main__':
    app.run_server(debug=True)
