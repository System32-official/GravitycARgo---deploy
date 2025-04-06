from dash import Dash, html, dcc, Input, Output, State, callback_context
import dash_leaflet as dl
import plotly.express as px
import plotly.graph_objects as go
from route_checkpoints import fetch_route_checkpoints, geocode_location
from osrm_services_demo import OSRMServices
import pandas as pd

app = Dash(__name__)
osrm = OSRMServices()

# Store for points
points_store = []

app.layout = html.Div([
    html.H1("Route Planning & Analysis Dashboard", style={'textAlign': 'center'}),
    
    # Main Container
    html.Div([
        # Left Panel - Input Controls
        html.Div([
            html.H3("Location Management"),
            dcc.Input(
                id='location-input',
                type='text',
                placeholder='Enter location name...',
                style={'width': '100%', 'marginBottom': '10px'}
            ),
            html.Button('Add Location', id='add-location', n_clicks=0),
            html.Button('Clear All', id='clear-locations', n_clicks=0),
            html.Div(id='locations-list', style={'marginTop': '20px'}),
            
            html.H3("Analysis Options", style={'marginTop': '20px'}),
            dcc.Tabs(id='analysis-tabs', value='checkpoints', children=[
                dcc.Tab(label='Checkpoints', value='checkpoints'),
                dcc.Tab(label='Route', value='route'),
                dcc.Tab(label='Round Trip', value='trip'),
                dcc.Tab(label='Distance Matrix', value='matrix'),
                dcc.Tab(label='Nearest Road', value='nearest'),
            ]),
            
            html.Div(id='analysis-options', style={'marginTop': '10px'}),
            
            html.Button('Calculate', id='calculate-button', 
                       style={'width': '100%', 'marginTop': '20px'},
                       n_clicks=0),
            
        ], style={'width': '25%', 'float': 'left', 'padding': '20px'}),
        
        # Right Panel - Map and Results
        html.Div([
            # Map
            dl.Map([
                dl.TileLayer(),
                dl.LayerGroup(id='map-markers'),
                dl.LayerGroup(id='route-layer')
            ], style={'height': '500px', 'margin': '10px'},
               center=[20, 0], zoom=2),
            
            # Results Panel
            html.Div(id='results-panel', 
                     style={'margin': '10px', 'padding': '10px',
                           'border': '1px solid #ddd'})
            
        ], style={'width': '70%', 'float': 'right'})
    ], style={'display': 'flex'}),
], style={'padding': '20px'})

@app.callback(
    [Output('locations-list', 'children'),
     Output('map-markers', 'children')],
    [Input('add-location', 'n_clicks'),
     Input('clear-locations', 'n_clicks')],
    [State('location-input', 'value')],
    prevent_initial_call=True
)
def update_locations(add_clicks, clear_clicks, location):
    global points_store
    ctx = callback_context
    
    if not ctx.triggered:
        return [], []
        
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'clear-locations':
        points_store = []
    elif button_id == 'add-location' and location:
        try:
            coords = geocode_location(location)
            points_store.append((location, coords))
        except Exception as e:
            return html.Div(f"Error: {str(e)}", style={'color': 'red'}), []
    
    locations_list = html.Ul([
        html.Li(f"{name} ({lat:.4f}, {lon:.4f})")
        for name, (lat, lon) in points_store
    ])
    
    markers = [
        dl.Marker(position=[lat, lon], children=dl.Tooltip(name))
        for name, (lat, lon) in points_store
    ]
    
    return locations_list, markers

@app.callback(
    Output('analysis-options', 'children'),
    Input('analysis-tabs', 'value')
)
def update_analysis_options(tab):
    if tab == 'checkpoints':
        return dcc.Input(
            id='num-checkpoints',
            type='number',
            placeholder='Number of checkpoints',
            min=2,
            value=5
        )
    return html.Div()

@app.callback(
    [Output('route-layer', 'children'),
     Output('results-panel', 'children')],
    Input('calculate-button', 'n_clicks'),
    [State('analysis-tabs', 'value'),
     State('num-checkpoints', 'value')],
    prevent_initial_call=True
)
def calculate_results(n_clicks, analysis_type, num_checkpoints):
    if not points_store or len(points_store) < 2:
        return [], html.Div("Please add at least 2 locations")
    
    coords = [coords for _, coords in points_store]
    
    try:
        if analysis_type == 'checkpoints':
            checkpoints = fetch_route_checkpoints(coords[0], coords[-1], num_checkpoints)
            
            route_line = dl.Polyline(
                positions=[(lat, lon) for lat, lon in checkpoints],
                color='blue',
                weight=2
            )
            
            results = html.Div([
                html.H3("Checkpoints"),
                html.Ul([
                    html.Li(f"Point {i+1}: ({lat:.4f}, {lon:.4f})")
                    for i, (lat, lon) in enumerate(checkpoints)
                ])
            ])
            
            return [route_line], results
            
        elif analysis_type == 'route':
            route_data = osrm.route(coords)
            if route_data['code'] == 'Ok':
                route = route_data['routes'][0]
                
                route_line = dl.Polyline(
                    positions=[[p[1], p[0]] for p in route['geometry']['coordinates']],
                    color='green',
                    weight=2
                )
                
                results = html.Div([
                    html.H3("Route Details"),
                    html.P(f"Distance: {route['distance']/1000:.1f} km"),
                    html.P(f"Duration: {route['duration']/3600:.1f} hours")
                ])
                
                return [route_line], results
                
        elif analysis_type == 'trip':
            trip_data = osrm.trip(coords)
            if trip_data['code'] == 'Ok':
                trip = trip_data['trips'][0]
                
                trip_line = dl.Polyline(
                    positions=[[p[1], p[0]] for p in trip['geometry']['coordinates']],
                    color='red',
                    weight=2
                )
                
                results = html.Div([
                    html.H3("Round Trip Details"),
                    html.P(f"Total Distance: {trip['distance']/1000:.1f} km"),
                    html.P(f"Total Duration: {trip['duration']/3600:.1f} hours")
                ])
                
                return [trip_line], results
                
        elif analysis_type == 'matrix':
            matrix_data = osrm.table(coords)
            if matrix_data['code'] == 'Ok':
                durations = pd.DataFrame(
                    matrix_data['durations'],
                    index=[p[0] for p in points_store],
                    columns=[p[0] for p in points_store]
                )
                
                fig = px.imshow(
                    durations/3600,  # Convert to hours
                    labels=dict(x="To", y="From", color="Hours"),
                    title="Travel Time Matrix"
                )
                
                return [], dcc.Graph(figure=fig)
                
        elif analysis_type == 'nearest':
            results = html.Div([
                html.H3("Nearest Road Results"),
                html.Ul([
                    html.Li([
                        html.Strong(f"{name}: "),
                        html.Span(f"{osrm.nearest(coords)['waypoints'][0]['distance']:.0f}m to nearest road")
                    ])
                    for name, coords in points_store
                ])
            ])
            
            return [], results
            
    except Exception as e:
        return [], html.Div(f"Error: {str(e)}", style={'color': 'red'})
    
    return [], html.Div("Analysis failed")

if __name__ == '__main__':
    app.run_server(debug=True)
