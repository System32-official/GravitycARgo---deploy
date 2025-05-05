"""
Visualization methods for the EnhancedContainer class
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.colors as colors

class ContainerVisualization:
    """Contains methods for visualizing container and packed items"""
    
    def __init__(self, dimensions, items, unpacked_reasons=None, unused_spaces=None):
        """Initialize with container properties"""
        self.dimensions = dimensions
        self.items = items
        self.unpacked_reasons = unpacked_reasons or {}
        self.unused_spaces = unused_spaces or []
        
        # Calculate utilization metrics
        self.container_volume = dimensions[0] * dimensions[1] * dimensions[2]
        self.packed_volume = sum(item.dimensions[0] * item.dimensions[1] * item.dimensions[2] 
                                for item in items if hasattr(item, 'position') and item.position)
        self.remaining_volume = self.container_volume - self.packed_volume
        self.volume_utilization = (self.packed_volume / self.container_volume * 100) if self.container_volume else 0
        
        # Calculate center of gravity if items have weights
        self.calculate_center_of_gravity()
    
    def calculate_center_of_gravity(self):
        """Calculate the center of gravity of all packed items"""
        total_weight = 0
        weighted_x, weighted_y, weighted_z = 0, 0, 0
        
        for item in self.items:
            if not hasattr(item, 'position') or not item.position or not hasattr(item, 'weight'):
                continue
                
            x, y, z = item.position
            l, w, h = item.dimensions
            weight = item.weight
            
            # Use center of item for CoG calculation
            center_x = x + l/2
            center_y = y + w/2
            center_z = z + h/2
            
            weighted_x += center_x * weight
            weighted_y += center_y * weight
            weighted_z += center_z * weight
            total_weight += weight
        
        if total_weight > 0:
            self.center_of_gravity = (weighted_x / total_weight, 
                                     weighted_y / total_weight, 
                                     weighted_z / total_weight)
        else:
            # Default to center of container if no weighted items
            self.center_of_gravity = (self.dimensions[0]/2, 
                                     self.dimensions[1]/2, 
                                     self.dimensions[2]/2)
    
    def create_interactive_visualization(self):
        """Create an interactive 3D visualization of the container and items"""
        # Create visualization with subplots
        fig = sp.make_subplots(
            rows=2, cols=2,
            specs=[
                [{'type': 'scene', 'rowspan': 2}, {'type': 'table'}],
                [None, {'type': 'table'}]
            ],
            column_widths=[0.7, 0.3],
            row_heights=[0.6, 0.4],
            subplot_titles=('3D Container View', 'Unpacked Items', 'Available Spaces')
        )
        
        # Add container and items to 3D view
        self.add_container_boundaries(fig)
        self.add_items_with_bundles(fig)
        self.add_center_of_gravity(fig)
        
        # Add unpacked items table
        self.add_unpacked_table(fig)
        
        # Add remaining space table
        if self.unused_spaces:
            empty_spaces_df = pd.DataFrame([
                {
                    'Location': f"({x:.2f}, {y:.2f}, {z:.2f})",
                    'Dimensions': f"{w:.2f}m × {d:.2f}m × {h:.2f}m",
                    'Volume': f"{w*d*h:.2f}m³"
                }
                for x, y, z, w, d, h in self.unused_spaces
            ])
            
            fig.add_trace(
                go.Table(
                    header=dict(
                        values=['Location', 'Dimensions', 'Volume'],
                        fill=dict(color='#e6f2ff'),
                        font=dict(color='black', size=12),
                        line=dict(color='#1f77b4', width=1),
                        align='left'
                    ),
                    cells=dict(
                        values=[empty_spaces_df[col] for col in empty_spaces_df.columns],
                        fill=dict(color=['white', '#f9f9f9']),
                        line=dict(color='#d3d3d3', width=1),
                        align='left'
                    )
                ),
                row=2, col=2
            )
        
        # Update layout
        fig.update_layout(
            height=1000,  # Increase height for better visibility
            title=dict(
                text=(f'3D Container Loading<br>'
                      f'<span style="color:#1f77b4">Volume Utilization: {self.volume_utilization:.1f}%</span><br>'
                      f'<span style="color:#ff7f0e">Remaining Volume: {self.remaining_volume:.2f}m³</span><br>'
                      f'<span style="color:#2ca02c">Items Packed: {len([i for i in self.items if hasattr(i, "position") and i.position])}/{len(self.items) + len(self.unpacked_reasons)}</span>'),
                x=0.5,
                y=0.95,
                font=dict(size=16)
            ),
            showlegend=True,
            legend=dict(
                groupclick="toggleitem",
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255, 255, 255, 0.8)"
            ),
            template="plotly_white"
        )
        
        return fig

    def add_container_boundaries(self, fig):
        """Add container walls and edges to the visualization"""
        x, y, z = self.dimensions
        
        # Add container walls with better visibility
        faces = [
            # Bottom face
            go.Mesh3d(
                x=[0, x, x, 0],
                y=[0, 0, y, y],
                z=[0, 0, 0, 0],
                color='rgba(173, 216, 230, 0.3)',
                opacity=0.3,
                showscale=False,
                name='Container Floor'
            ),
            # Back wall
            go.Mesh3d(
                x=[0, x, x, 0],
                y=[y, y, y, y],
                z=[0, 0, z, z],
                color='rgba(173, 216, 230, 0.3)',
                opacity=0.3,
                showscale=False,
                name='Container Back'
            ),
            # Left wall
            go.Mesh3d(
                x=[0, 0, 0, 0],
                y=[0, y, y, 0],
                z=[0, 0, z, z],
                color='rgba(173, 216, 230, 0.3)',
                opacity=0.3,
                showscale=False,
                name='Container Left'
            )
        ]
        
        # Add container edges for better definition
        edges = [
            # Floor edges
            go.Scatter3d(x=[0, x], y=[0, 0], z=[0, 0], mode='lines', line=dict(color='black', width=3), showlegend=False),
            go.Scatter3d(x=[0, 0], y=[0, y], z=[0, 0], mode='lines', line=dict(color='black', width=3), showlegend=False),
            go.Scatter3d(x=[x, x], y=[0, y], z=[0, 0], mode='lines', line=dict(color='black', width=3), showlegend=False),
            go.Scatter3d(x=[0, x], y=[y, y], z=[0, 0], mode='lines', line=dict(color='black', width=3), showlegend=False),
            # Vertical edges
            go.Scatter3d(x=[0, 0], y=[0, 0], z=[0, z], mode='lines', line=dict(color='black', width=3), showlegend=False),
            go.Scatter3d(x=[x, x], y=[0, 0], z=[0, z], mode='lines', line=dict(color='black', width=3), showlegend=False),
            go.Scatter3d(x=[x, x], y=[y, y], z=[0, z], mode='lines', line=dict(color='black', width=3), showlegend=False),
            go.Scatter3d(x=[0, 0], y=[y, y], z=[0, z], mode='lines', line=dict(color='black', width=3), showlegend=False),
            # Top edges
            go.Scatter3d(x=[0, x], y=[0, 0], z=[z, z], mode='lines', line=dict(color='black', width=3), showlegend=False),
            go.Scatter3d(x=[0, 0], y=[0, y], z=[z, z], mode='lines', line=dict(color='black', width=3), showlegend=False),
            go.Scatter3d(x=[x, x], y=[0, y], z=[z, z], mode='lines', line=dict(color='black', width=3), showlegend=False),
            go.Scatter3d(x=[0, x], y=[y, y], z=[z, z], mode='lines', line=dict(color='black', width=3), showlegend=False)
        ]
        
        # Add grid lines for better space perception
        grid_lines = []
        grid_spacing = min(x, y, z) / 10  # Create grid with 10 divisions
        
        # Add floor grid
        for i in np.arange(0, x + grid_spacing, grid_spacing):
            grid_lines.append(go.Scatter3d(x=[i, i], y=[0, y], z=[0, 0], 
                                         mode='lines', line=dict(color='lightgray', width=1), showlegend=False))
        for i in np.arange(0, y + grid_spacing, grid_spacing):
            grid_lines.append(go.Scatter3d(x=[0, x], y=[i, i], z=[0, 0], 
                                         mode='lines', line=dict(color='lightgray', width=1), showlegend=False))

        # Add all elements to the figure
        for face in faces:
            fig.add_trace(face, row=1, col=1)
        for edge in edges:
            fig.add_trace(edge, row=1, col=1)
        for grid in grid_lines:
            fig.add_trace(grid, row=1, col=1)

        # Add measurement indicators
        self.add_dimension_indicators(fig, x, y, z)

        # Update scene layout for better visualization
        fig.update_scenes(
            camera=dict(
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=0),
                eye=dict(x=1.5, y=1.5, z=1.5)
            ),
            aspectmode='data',
            xaxis=dict(
                range=[-x*0.1, x*1.1],
                title=dict(text="Length (m)", font=dict(size=12)),
                showbackground=True,
                backgroundcolor="rgba(240, 240, 240, 0.5)"
            ),
            yaxis=dict(
                range=[-y*0.1, y*1.1],
                title=dict(text="Width (m)", font=dict(size=12)),
                showbackground=True,
                backgroundcolor="rgba(240, 240, 240, 0.5)"
            ),
            zaxis=dict(
                range=[-z*0.1, z*1.1],
                title=dict(text="Height (m)", font=dict(size=12)),
                showbackground=True,
                backgroundcolor="rgba(240, 240, 240, 0.5)"
            )
        )

    def add_dimension_indicators(self, fig, x, y, z):
        """Add dimension indicators for the container with improved visibility and clarity"""
        # Define consistent offset for all dimension indicators (in meters)
        offset = min(x, y, z) * 0.1  # Fixed percentage of the smallest dimension
        min_offset = 0.2  # Minimum offset to ensure visibility in small containers
        offset = max(offset, min_offset)
        
        # Define colors for each dimension with good contrast
        length_color = 'rgb(31, 119, 180)'  # Blue
        width_color = 'rgb(255, 127, 14)'   # Orange
        height_color = 'rgb(44, 160, 44)'   # Green
        
        # Length indicator (X-axis)
        fig.add_trace(
            go.Scatter3d(
                x=[0, x],
                y=[-offset, -offset],
                z=[-offset, -offset],
                mode='lines+text',
                line=dict(color=length_color, width=5),
                text=['', f'{x}m'],
                textposition='middle right',
                textfont=dict(
                    size=14, 
                    color=length_color,
                    family='Arial Black'
                ),
                name='Length (X)',
                showlegend=True
            ),
            row=1, col=1
        )
        
        # Width indicator (Y-axis)
        fig.add_trace(
            go.Scatter3d(
                x=[-offset, -offset],
                y=[0, y],
                z=[-offset, -offset],
                mode='lines+text',
                line=dict(color=width_color, width=5),
                text=['', f'{y}m'],
                textposition='middle right',
                textfont=dict(
                    size=14, 
                    color=width_color,
                    family='Arial Black'
                ),
                name='Width (Y)',
                showlegend=True
            ),
            row=1, col=1
        )
        
        # Height indicator (Z-axis)
        fig.add_trace(
            go.Scatter3d(
                x=[-offset, -offset],
                y=[-offset, -offset],
                z=[0, z],
                mode='lines+text',
                line=dict(color=height_color, width=5),
                text=['', f'{z}m'],
                textposition='middle right',
                textfont=dict(
                    size=14, 
                    color=height_color,
                    family='Arial Black'
                ),
                name='Height (Z)',
                showlegend=True
            ),
            row=1, col=1
        )
        
        # Add small end markers to mimic arrowheads
        marker_size = min(x, y, z) * 0.04  # Scale marker size to container
        min_marker_size = 0.1
        marker_size = max(marker_size, min_marker_size)
        
        # Add endpoint markers (create illusion of arrows)
        fig.add_trace(
            go.Scatter3d(
                x=[x],
                y=[-offset],
                z=[-offset],
                mode='markers',
                marker=dict(
                    size=marker_size,
                    color=length_color,
                    symbol='diamond'
                ),
                showlegend=False
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter3d(
                x=[-offset],
                y=[y],
                z=[-offset],
                mode='markers',
                marker=dict(
                    size=marker_size,
                    color=width_color,
                    symbol='diamond'
                ),
                showlegend=False
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter3d(
                x=[-offset],
                y=[-offset],
                z=[z],
                mode='markers',
                marker=dict(
                    size=marker_size,
                    color=height_color,
                    symbol='diamond'
                ),
                showlegend=False
            ),
            row=1, col=1
        )

    def add_item_to_plot(self, fig, item):
        """Add an item to the 3D plot"""
        if not hasattr(item, 'position') or not item.position:
            return
            
        x, y, z = item.position
        l, w, h = item.dimensions
        
        # Define vertices
        vertices = [
            [x, y, z], [x+l, y, z], [x+l, y+w, z], [x, y+w, z],
            [x, y, z+h], [x+l, y, z+h], [x+l, y+w, z+h], [x, y+w, z+h]
        ]
        
        # Define triangular faces for proper mesh rendering
        # Optimized definition with all triangular faces for a complete cube
        i = [0, 0, 1, 1, 2, 2, 3, 3, 0, 0, 4, 4]  # First vertex index
        j = [1, 3, 2, 6, 3, 7, 0, 4, 4, 5, 5, 7]  # Second vertex index
        k = [3, 2, 6, 7, 7, 6, 4, 7, 5, 1, 6, 3]  # Third vertex index
        
        # Add top face triangles to complete the cube
        i.extend([5, 5])
        j.extend([6, 7])
        k.extend([7, 6])

        # Create hover text
        hover_text = f"""
        Item: {item.name if hasattr(item, 'name') else 'Unnamed Item'}<br>
        Position: ({x:.2f}, {y:.2f}, {z:.2f})<br>
        Dimensions: {l:.2f}m × {w:.2f}m × {h:.2f}m<br>
        Weight: {item.weight if hasattr(item, 'weight') else 'N/A'}kg<br>
        Quantity: {item.quantity if hasattr(item, 'quantity') else 1}<br>
        Fragility: {item.fragility if hasattr(item, 'fragility') else 'N/A'}
        """

        # Set item color
        color = item.color if hasattr(item, 'color') else self.get_random_color(item)

        # Add complete 3D mesh with improved rendering
        fig.add_trace(
            go.Mesh3d(
                x=[v[0] for v in vertices],
                y=[v[1] for v in vertices],
                z=[v[2] for v in vertices],
                i=i,
                j=j,
                k=k,
                color=color,
                opacity=0.85,  # Slightly transparent for better visualization
                flatshading=True,
                lighting=dict(
                    ambient=0.7,
                    diffuse=1.0,
                    fresnel=0.1,
                    specular=0.7, 
                    roughness=0.3
                ),
                hovertext=hover_text,
                hoverinfo='text',
                showscale=False,
                name=item.name if hasattr(item, 'name') else f"Item at ({x:.1f},{y:.1f},{z:.1f})"
            ),
            row=1, col=1
        )
        
        # Add edges for each box for better definition
        edges = [
            # Bottom face
            ([x, x+l], [y, y], [z, z]), ([x+l, x+l], [y, y+w], [z, z]),
            ([x+l, x], [y+w, y+w], [z, z]), ([x, x], [y+w, y], [z, z]),
            # Top face
            ([x, x+l], [y, y], [z+h, z+h]), ([x+l, x+l], [y, y+w], [z+h, z+h]),
            ([x+l, x], [y+w, y+w], [z+h, z+h]), ([x, x], [y+w, y], [z+h, z+h]),
            # Vertical edges
            ([x, x], [y, y], [z, z+h]), ([x+l, x+l], [y, y], [z, z+h]),
            ([x+l, x+l], [y+w, y+w], [z, z+h]), ([x, x], [y+w, y+w], [z, z+h])
        ]
        
        for edge in edges:
            fig.add_trace(
                go.Scatter3d(
                    x=edge[0], y=edge[1], z=edge[2],
                    mode='lines',
                    line=dict(color='black', width=1),
                    showlegend=False
                ),
                row=1, col=1
            )

    def get_random_color(self, item):
        """Generate a consistent color based on item properties"""
        # Use a hash of the item's properties to get a consistent color
        if hasattr(item, 'name'):
            hash_val = hash(item.name) % 10
        else:
            # Use position as fallback for consistent coloring
            if hasattr(item, 'position') and item.position:
                hash_val = int(sum(item.position)) % 10
            else:
                hash_val = id(item) % 10
                
        # Use plotly color scale for a nice set of colors
        color_scale = colors.qualitative.Plotly
        return color_scale[hash_val % len(color_scale)]

    def add_items_with_bundles(self, fig):
        """Add items and their bundle subdivisions to the visualization"""
        for item in self.items:
            if not hasattr(item, 'position') or not item.position:
                continue
                
            self.add_item_to_plot(fig, item)
            
            # Add bundle subdivisions if applicable
            if (hasattr(item, 'bundle') and item.bundle == 'YES' and 
                hasattr(item, 'quantity') and item.quantity > 1 and
                hasattr(item, 'original_dims')):
                self.add_bundle_subdivisions(fig, item)

    def add_bundle_subdivisions(self, fig, item):
        """Add visual subdivisions for bundled items"""
        x, y, z = item.position
        orig_l, orig_w, orig_h = item.original_dims
        qty = item.quantity
        
        # Calculate subdivision dimensions
        nx = int(item.dimensions[0] / orig_l)
        ny = int(item.dimensions[1] / orig_w)
        nz = int(item.dimensions[2] / orig_h)
        
        # Add inner edges for subdivisions
        for i in range(nx + 1):
            for j in range(ny + 1):
                for k in range(nz + 1):
                    if i * j * k < qty:  # Only add subdivisions up to quantity
                        self.add_subdivision_edges(fig, 
                                           (x + i * orig_l, y + j * orig_w, z + k * orig_h),
                                           (orig_l, orig_w, orig_h),
                                           item.color if hasattr(item, 'color') else 'gray')

    def add_subdivision_edges(self, fig, pos, dims, color):
        """Add edges for bundle subdivisions"""
        x, y, z = pos
        l, w, h = dims
        
        # Define edges with thinner lines
        edges = [
            # Bottom face
            ([x, x+l], [y, y], [z, z]), ([x+l, x+l], [y, y+w], [z, z]),
            ([x+l, x], [y+w, y+w], [z, z]), ([x, x], [y+w, y], [z, z]),
            # Top face
            ([x, x+l], [y, y], [z+h, z+h]), ([x+l, x+l], [y, y+w], [z+h, z+h]),
            ([x+l, x], [y+w, y+w], [z+h, z+h]), ([x, x], [y+w, y], [z+h, z+h]),
            # Vertical edges
            ([x, x], [y, y], [z, z+h]), ([x+l, x+l], [y, y], [z, z+h]),
            ([x+l, x+l], [y+w, y+w], [z, z+h]), ([x, x], [y+w, y+w], [z, z+h])
        ]
        
        for edge in edges:
            fig.add_trace(
                go.Scatter3d(
                    x=edge[0], y=edge[1], z=edge[2],
                    mode='lines',
                    line=dict(color=color, width=0.5, dash='dot'),
                    showlegend=False
                ),
                row=1, col=1
            )

    def add_center_of_gravity(self, fig):
        """Add center of gravity indicator to the visualization"""
        if not hasattr(self, 'center_of_gravity'):
            return
            
        x, y, z = self.center_of_gravity
        
        # Add sphere at CoG
        fig.add_trace(
            go.Scatter3d(
                x=[x], y=[y], z=[z],
                mode='markers',
                marker=dict(
                    size=12,
                    symbol='circle',
                    color='red',
                    line=dict(color='darkred', width=2),
                    opacity=0.8
                ),
                name='Center of Gravity',
                hovertext=f'Center of Gravity<br>x: {x:.2f}, y: {y:.2f}, z: {z:.2f}',
                hoverinfo='text'
            ),
            row=1, col=1
        )
        
        # Add crosshairs
        self.add_cog_crosshairs(fig)

    def add_cog_crosshairs(self, fig):
        """Add crosshair lines through center of gravity"""
        if not hasattr(self, 'center_of_gravity'):
            return
            
        x, y, z = self.center_of_gravity
        dims = self.dimensions
        
        # Add crosshair lines
        lines = [
            # Vertical line
            ([x, x], [y, y], [0, dims[2]]),
            # Width line
            ([x, x], [0, dims[1]], [z, z]),
            # Length line
            ([0, dims[0]], [y, y], [z, z])
        ]
        
        for i, line in enumerate(lines):
            fig.add_trace(
                go.Scatter3d(
                    x=line[0], y=line[1], z=line[2],
                    mode='lines',
                    line=dict(color='red', width=1, dash='dash'),
                    showlegend=i == 0,  # Only show legend for the first line
                    name='CoG Crosshairs' if i == 0 else None
                ),
                row=1, col=1
            )

    def add_unpacked_table(self, fig):
        """Add table showing unpacked items and reasons"""
        if not self.unpacked_reasons:
            return
            
        df = pd.DataFrame([
            {
                'Item': name,
                'Reason': reason,
                'Dimensions': f"{item.dimensions[0]:.2f}×{item.dimensions[1]:.2f}×{item.dimensions[2]:.2f}m",
                'Weight': f"{item.weight:.2f}kg" if hasattr(item, 'weight') else 'N/A'
            }
            for name, (reason, item) in self.unpacked_reasons.items()
        ])
        
        fig.add_trace(
            go.Table(
                header=dict(
                    values=list(df.columns),
                    fill=dict(color='#f2f2f2'),
                    font=dict(size=12, color='black'),
                    line=dict(color='#7f7f7f', width=1),
                    align='left'
                ),
                cells=dict(
                    values=[df[col] for col in df.columns],
                    fill=dict(color=['white', '#f9f9f9']),
                    font=dict(size=11),
                    line=dict(color='#d3d3d3', width=1),
                    align='left'
                )
            ),
            row=1, col=2
        )

    def create_dashboard(self, app):
        """Create a Dash app dashboard for the container visualization"""
        app.layout = html.Div([
            html.H1("Interactive Container Loading Visualization", 
                   style={'textAlign': 'center', 'marginBottom': '20px'}),
            
            html.Div([
                html.Div([
                    html.H3("Container Statistics", style={'marginBottom': '10px'}),
                    html.Div([
                        html.P(f"Container Dimensions: {self.dimensions[0]}m × {self.dimensions[1]}m × {self.dimensions[2]}m"),
                        html.P(f"Total Container Volume: {self.container_volume:.2f}m³"),
                        html.P(f"Volume Utilization: {self.volume_utilization:.1f}%"),
                        html.P(f"Items Packed: {len([i for i in self.items if hasattr(i, 'position') and i.position])}/{len(self.items) + len(self.unpacked_reasons)}")
                    ], style={'padding': '10px', 'backgroundColor': '#f9f9f9', 'borderRadius': '5px'})
                ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                
                html.Div([
                    html.H3("Visualization Options", style={'marginBottom': '10px'}),
                    html.Label("View Options:"),
                    dcc.Checklist(
                        id='view-options',
                        options=[
                            {'label': ' Show Grid', 'value': 'grid'},
                            {'label': ' Show CoG', 'value': 'cog'},
                            {'label': ' Show Bundles', 'value': 'bundles'}
                        ],
                        value=['grid', 'cog', 'bundles'],
                        inline=True,
                        style={'marginBottom': '10px'}
                    ),
                    html.Label("Color Scheme:"),
                    dcc.RadioItems(
                        id='color-scheme',
                        options=[
                            {'label': ' Standard', 'value': 'standard'},
                            {'label': ' Weight-based', 'value': 'weight'},
                            {'label': ' Category-based', 'value': 'category'}
                        ],
                        value='standard',
                        inline=True
                    )
                ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginLeft': '20px'}),
                
                html.Div([
                    html.H3("Container Actions", style={'marginBottom': '10px'}),
                    html.Button("Reset View", id="reset-view-button", 
                               style={'marginRight': '10px', 'padding': '10px', 'backgroundColor': '#4CAF50', 'color': 'white', 'border': 'none', 'borderRadius': '5px'}),
                    html.Button("Download Data", id="download-button",
                               style={'padding': '10px', 'backgroundColor': '#008CBA', 'color': 'white', 'border': 'none', 'borderRadius': '5px'})
                ], style={'width': '30%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginLeft': '20px'})
            ], style={'marginBottom': '20px'}),
            
            dcc.Graph(
                id='container-3d-view',
                figure=self.create_interactive_visualization(),
                style={'height': '800px'}
            )
        ], style={'padding': '20px', 'fontFamily': 'Arial, sans-serif'})
        
        @app.callback(
            Output('container-3d-view', 'figure'),
            [Input('view-options', 'value'),
             Input('color-scheme', 'value'),
             Input('reset-view-button', 'n_clicks')]
        )
        def update_visualization(view_options, color_scheme, n_clicks):
            # This is a placeholder for the callback implementation
            # In a real application, you'd update the visualization based on the inputs
            return self.create_interactive_visualization()
        
        return app