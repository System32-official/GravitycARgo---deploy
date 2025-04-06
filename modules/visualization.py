"""
Visualization functions for the container packing application
"""
import plotly.graph_objects as go
import numpy as np
import pandas as pd

def create_interactive_visualization(container, container_info=None):
    """Create an interactive 3D visualization of packed items in the container"""
    fig = go.Figure()

    x, y, z = container.dimensions
    
    # Create title with container information
    title_text = 'Container Loading Visualization<br>'
    if container_info:
        title_text += f'Type: {container_info["type"]}<br>'
        title_text += f'Transport Mode: {container_info["transport_mode"]}<br>'
        if "route_temperature" in container_info:
            title_text += f'Route Temperature: {container_info["route_temperature"]}°C<br>'
    title_text += f'Dimensions: {x:.2f}m × {y:.2f}m × {z:.2f}m'

    # Add container walls with transparency
    fig.add_trace(go.Mesh3d(
        # 8 vertices of a cube
        x=[0, x, x, 0, 0, x, x, 0],
        y=[0, 0, y, y, 0, 0, y, y],
        z=[0, 0, 0, 0, z, z, z, z],
        i=[0, 0, 0, 1, 4, 4, 4, 5],  # Index of vertices for triangles
        j=[1, 2, 5, 6, 6, 7, 7, 6],
        k=[2, 3, 7, 3, 6, 7, 6, 7],
        opacity=0.2,
        color='lightgrey',
        flatshading=True,
        lighting=dict(
            ambient=0.8,
            diffuse=0.9,
            fresnel=0.2,
            specular=0.5,
            roughness=0.5
        ),
        showlegend=False,
        hoverinfo='none'
    ))

    # Add items with proper 3D box rendering
    for item in container.items:
        x0, y0, z0 = item.position
        dx, dy, dz = item.dimensions

        # Define all 8 vertices of the box
        vertices = [
            [x0, y0, z0], [x0+dx, y0, z0], [x0+dx, y0+dy, z0], [x0, y0+dy, z0],  # bottom
            [x0, y0, z0+dz], [x0+dx, y0, z0+dz], [x0+dx, y0+dy, z0+dz], [x0, y0+dy, z0+dz]  # top
        ]

        # Use item.color directly if it has been set (especially for temperature-sensitive items)
        # This ensures temperature-sensitive items with needs_insulation flag get the sky blue color
        if hasattr(item, 'color') and item.color:
            color = item.color  # Use the color already set in the item
        else:
            # Fallback coloring based on fragility if item.color is not set
            if hasattr(item, 'temperature_sensitivity') and item.temperature_sensitivity:
                if hasattr(item, 'needs_insulation') and item.needs_insulation:
                    color = 'rgb(0, 128, 255)'  # Sky blue for temperature sensitive items needing insulation
                else:
                    color = 'rgba(135, 206, 250, 0.9)'  # Light blue for temperature sensitive items
            elif item.fragility == 'HIGH':
                color = 'rgba(255, 99, 71, 0.9)'  # Tomato red
            elif item.fragility == 'MEDIUM':
                color = 'rgba(30, 144, 255, 0.9)'  # Dodger blue
            else:
                color = 'rgba(60, 179, 113, 0.9)'  # Medium sea green

        # Create triangular faces for complete box
        i = [0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5]  # First vertex index
        j = [1, 2, 5, 6, 6, 7, 7, 4, 5, 6, 6, 7]  # Second vertex index
        k = [2, 3, 6, 7, 7, 4, 4, 5, 1, 2, 2, 3]  # Third vertex index

        # Add box as a mesh with all faces colored
        hover_text = (f'{item.name}<br>'
                     f'Position: ({x0:.2f}, {y0:.2f}, {z0:.2f})<br>'
                     f'Dimensions: {dx:.2f}×{dy:.2f}×{dz:.2f}<br>'
                     f'Weight: {item.weight:.2f}kg<br>'
                     f'Fragility: {item.fragility}')
                     
        if hasattr(item, 'temperature_sensitivity') and item.temperature_sensitivity:
            hover_text += f'<br>Temperature Sensitivity: {item.temperature_sensitivity}'
            if hasattr(item, 'needs_insulation') and item.needs_insulation:
                hover_text += '<br>Requires Insulation'

        fig.add_trace(go.Mesh3d(
            x=[v[0] for v in vertices],
            y=[v[1] for v in vertices],
            z=[v[2] for v in vertices],
            i=i,
            j=j,
            k=k,
            color=color,
            opacity=0.95,
            flatshading=True,
            lighting=dict(
                ambient=0.8,
                diffuse=0.9,
                fresnel=0.2,
                specular=0.5,
                roughness=0.5
            ),
            name=item.name,
            showlegend=True,
            hoverinfo='text',
            hovertext=hover_text
        ))

        # Add edges for better definition
        edges = [
            # Bottom face
            ([x0, x0+dx], [y0, y0], [z0, z0]),
            ([x0+dx, x0+dx], [y0, y0+dy], [z0, z0]),
            ([x0+dx, x0], [y0+dy, y0+dy], [z0, z0]),
            ([x0, x0], [y0+dy, y0], [z0, z0]),
            # Top face
            ([x0, x0+dx], [y0, y0], [z0+dz, z0+dz]),
            ([x0+dx, x0+dx], [y0, y0+dy], [z0+dz, z0+dz]),
            ([x0+dx, x0], [y0+dy, y0+dy], [z0+dz, z0+dz]),
            ([x0, x0], [y0+dy, y0], [z0+dz, z0+dz]),
            # Vertical edges
            ([x0, x0], [y0, y0], [z0, z0+dz]),
            ([x0+dx, x0+dx], [y0, y0], [z0, z0+dz]),
            ([x0+dx, x0+dx], [y0+dy, y0+dy], [z0, z0+dz]),
            ([x0, x0], [y0+dy, y0+dy], [z0, z0+dz])
        ]

        # Add black edges for better definition
        for edge in edges:
            fig.add_trace(go.Scatter3d(
                x=edge[0], y=edge[1], z=edge[2],
                mode='lines',
                line=dict(color='black', width=2),
                showlegend=False,
                hoverinfo='none'
            ))

    # Update layout with improved title and annotations
    fig.update_layout(
        scene=dict(
            aspectmode='data',
            camera=dict(
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=0),
                eye=dict(x=2, y=2, z=1.5)
            ),
            xaxis=dict(title=f'Length: {x:.2f}m'),
            yaxis=dict(title=f'Width: {y:.2f}m'),
            zaxis=dict(title=f'Height: {z:.2f}m'),
            dragmode='turntable'
        ),
        showlegend=True,
        title=dict(
            text=title_text,
            x=0.5,
            y=0.95
        ),
        margin=dict(l=0, r=0, t=100, b=0)  # Increased top margin for title
    )

    return fig

def add_unpacked_table(fig, container):
    """Add table showing unpacked items and reasons"""
    if container.unpacked_reasons:
        df = pd.DataFrame([
            {
                'Item': name,
                'Reason': reason,
                'Dimensions': f"{item.dimensions[0]}x{item.dimensions[1]}x{item.dimensions[2]}",
                'Weight': item.weight
            }
            for name, (reason, item) in container.unpacked_reasons.items()
        ])
        
        fig.add_trace(
            go.Table(
                header=dict(
                    values=['Item', 'Reason', 'Dimensions', 'Weight'],
                    fill_color='paleturquoise',
                    align='left',
                    font=dict(size=12)
                ),
                cells=dict(
                    values=[
                        df['Item'],
                        df['Reason'],
                        df['Dimensions'],
                        df['Weight']
                    ],
                    fill_color='lavender',
                    align='left',
                    font=dict(size=11)
                ),
                columnwidth=[2, 4, 2, 1]
            ),
            row=1, col=2
        )
        
        # Add header for unpacked items section
        fig.update_layout(
            annotations=[
                dict(
                    text="Unpacked Items",
                    xref="paper",
                    yref="paper",
                    x=1.0,
                    y=1.0,
                    xanchor="right",
                    yanchor="bottom",
                    font=dict(size=14),
                    showarrow=False
                )
            ]
        )