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

class ContainerVisualization:
    """Contains methods for visualizing container and packed items"""
    
    def create_interactive_visualization(self):
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
                header=dict(values=['Location', 'Dimensions', 'Volume'],
                          fill=dict(color='lightgray'),
                          align='left'),
                cells=dict(values=[empty_spaces_df[col] for col in empty_spaces_df.columns],
                          align='left')
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=1000,  # Increase height for better visibility
            title=dict(
                text=(f'3D Container Loading<br>'
                      f'Volume Utilization: {self.volume_utilization:.1f}%<br>'
                      f'Remaining Volume: {self.remaining_volume:.2f}m³<br>'
                      f'Items Packed: {len(self.items)}/{len(self.items) + len(self.unpacked_reasons)}'),
                x=0.5,
                y=0.95
            ),
            showlegend=True
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
                color='lightblue',
                opacity=0.3,
                showscale=False,
                name='Container Floor'
            ),
            # Back wall
            go.Mesh3d(
                x=[0, x, x, 0],
                y=[y, y, y, y],
                z=[0, 0, z, z],
                color='lightblue',
                opacity=0.3,
                showscale=False,
                name='Container Back'
            ),
            # Left wall
            go.Mesh3d(
                x=[0, 0, 0, 0],
                y=[0, y, y, 0],
                z=[0, 0, z, z],
                color='lightblue',
                opacity=0.3,
                showscale=False,
                name='Container Left'
            )
        ]
        
        # Add container edges for better definition
        edges = [
            # Floor edges
            go.Scatter3d(x=[0, x], y=[0, 0], z=[0, 0], mode='lines', line=dict(color='black', width=3)),
            go.Scatter3d(x=[0, 0], y=[0, y], z=[0, 0], mode='lines', line=dict(color='black', width=3)),
            go.Scatter3d(x=[x, x], y=[0, y], z=[0, 0], mode='lines', line=dict(color='black', width=3)),
            go.Scatter3d(x=[0, x], y=[y, y], z=[0, 0], mode='lines', line=dict(color='black', width=3)),
            # Vertical edges
            go.Scatter3d(x=[0, 0], y=[0, 0], z=[0, z], mode='lines', line=dict(color='black', width=3)),
            go.Scatter3d(x=[x, x], y=[0, 0], z=[0, z], mode='lines', line=dict(color='black', width=3)),
            go.Scatter3d(x=[x, x], y=[y, y], z=[0, z], mode='lines', line=dict(color='black', width=3)),
            go.Scatter3d(x=[0, 0], y=[y, y], z=[0, z], mode='lines', line=dict(color='black', width=3)),
            # Top edges
            go.Scatter3d(x=[0, x], y=[0, 0], z=[z, z], mode='lines', line=dict(color='black', width=3)),
            go.Scatter3d(x=[0, 0], y=[0, y], z=[z, z], mode='lines', line=dict(color='black', width=3)),
            go.Scatter3d(x=[x, x], y=[0, y], z=[z, z], mode='lines', line=dict(color='black', width=3)),
            go.Scatter3d(x=[0, x], y=[y, y], z=[z, z], mode='lines', line=dict(color='black', width=3))
        ]
        
        # Add grid lines for better space perception
        grid_lines = []
        grid_spacing = min(x, y, z) / 10  # Create grid with 10 divisions
        
        # Add floor grid
        for i in np.arange(0, x + grid_spacing, grid_spacing):
            grid_lines.append(go.Scatter3d(x=[i, i], y=[0, y], z=[0, 0], 
                                         mode='lines', line=dict(color='gray', width=1)))
        for i in np.arange(0, y + grid_spacing, grid_spacing):
            grid_lines.append(go.Scatter3d(x=[0, x], y=[i, i], z=[0, 0], 
                                         mode='lines', line=dict(color='gray', width=1)))

        # Add all elements to the figure
        for face in faces:
            fig.add_trace(face)
        for edge in edges:
            fig.add_trace(edge)
        for grid in grid_lines:
            fig.add_trace(grid)

        # Update scene layout for better visualization
        fig.update_scenes(
            camera=dict(
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=0),
                eye=dict(x=1.5, y=1.5, z=1.5)
            ),
            aspectmode='data',
            xaxis=dict(range=[-x*0.1, x*1.1]),
            yaxis=dict(range=[-y*0.1, y*1.1]),
            zaxis=dict(range=[-z*0.1, z*1.1])
        )

    def add_item_to_plot(self, fig, item):
        """Add an item to the 3D plot"""
        x, y, z = item.position
        l, w, h = item.dimensions
        
        # Define vertices
        vertices = [
            [x, y, z], [x+l, y, z], [x+l, y+w, z], [x, y+w, z],
            [x, y, z+h], [x+l, y, z+h], [x+l, y+w, z+h], [x, y+w, z+h]
        ]
        
        # Define faces using vertices
        faces = [
            [vertices[0], vertices[1], vertices[2], vertices[3]],  # bottom
            [vertices[4], vertices[5], vertices[6], vertices[7]],  # top
            [vertices[0], vertices[1], vertices[5], vertices[4]],  # front
            [vertices[2], vertices[3], vertices[7], vertices[6]],  # back
            [vertices[1], vertices[2], vertices[6], vertices[5]],  # right
            [vertices[0], vertices[3], vertices[7], vertices[4]]   # left
        ]

        # Add faces
        for face in faces:
            fig.add_trace(go.Mesh3d(
                x=[v[0] for v in face],
                y=[v[1] for v in face],
                z=[v[2] for v in face],
                i=[0, 0, 0, 0],
                j=[1, 2, 3, 1],
                k=[2, 3, 1, 2],
                color=item.color,
                opacity=0.7,
                hovertext=f"""
                Item: {item.name}<br>
                Position: ({x:.2f}, {y:.2f}, {z:.2f})<br>
                Dimensions: {l:.2f}m × {w:.2f}m × {h:.2f}m<br>
                Weight: {item.weight}kg<br>
                Quantity: {item.quantity}<br>
                Fragility: {item.fragility}
                """,
                hoverinfo='text',
                showscale=False,
                name=item.name
            ))
        
        # Add edges for each box
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
            fig.add_trace(go.Scatter3d(
                x=edge[0], y=edge[1], z=edge[2],
                mode='lines',
                line=dict(color='black', width=1),
                showlegend=False
            ))

    def add_items_with_bundles(self, fig):
        """Add items and their bundle subdivisions to the visualization"""
        for item in self.items:
            if not item.position:
                continue
            self.add_item_to_plot(fig, item)
            if item.bundle == 'YES' and item.quantity > 1:
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
                                           item.color)

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
            fig.add_trace(go.Scatter3d(
                x=edge[0], y=edge[1], z=edge[2],
                mode='lines',
                line=dict(color=color, width=0.5, dash='dot'),
                showlegend=False
            ))

    def add_center_of_gravity(self, fig):
        """Add center of gravity indicator to the visualization"""
        x, y, z = self.center_of_gravity
        
        # Add sphere at COG
        fig.add_trace(go.Scatter3d(
            x=[x], y=[y], z=[z],
            mode='markers',
            marker=dict(
                size=10,
                symbol='circle',
                color='red',
                line=dict(color='black', width=2)
            ),
            name='Center of Gravity',
            hovertext=f'Center of Gravity<br>x: {x:.2f}, y: {y:.2f}, z: {z:.2f}',
            hoverinfo='text'
        ))
        
        # Add crosshairs
        self.add_cog_crosshairs(fig)

    def add_cog_crosshairs(self, fig):
        """Add crosshair lines through center of gravity"""
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
        
        for line in lines:
            fig.add_trace(go.Scatter3d(
                x=line[0], y=line[1], z=line[2],
                mode='lines',
                line=dict(color='red', width=1, dash='dash'),
                showlegend=False
            ))

    def add_unpacked_table(self, fig):
        """Add table showing unpacked items and reasons"""
        if self.unpacked_reasons:
            df = pd.DataFrame([
                {
                    'Item': name,
                    'Reason': reason,
                    'Dimensions': f"{item.dimensions[0]}x{item.dimensions[1]}x{item.dimensions[2]}",
                    'Weight': item.weight
                }
                for name, (reason, item) in self.unpacked_reasons.items()
            ])
            
            fig.add_trace(
                go.Table(
                    header=dict(
                        values=list(df.columns),
                        align='left'
                    ),
                    cells=dict(
                        values=[df[col] for col in df.columns],
                        align='left'
                    )
                ),
                row=1, col=2
            )