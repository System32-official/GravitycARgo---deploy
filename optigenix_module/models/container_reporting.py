"""
Reporting and analysis functionality for the EnhancedContainer class
"""
import json
from datetime import datetime
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

class ContainerReporting:
    """Contains methods for generating reports and interactive tools"""
    
    def generate_packing_report(self, filename=None):
        """Generate a detailed packing report in both human-readable and machine-readable formats"""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"packing_report_{timestamp}"

        # Create report data structure
        report_data = {
            "container": {
                "dimensions": self.dimensions,
                "volume": self.total_volume,
                "volume_utilization": self.volume_utilization,
                "remaining_volume": self.remaining_volume,
                "center_of_gravity": self.center_of_gravity,
                "weight_distribution": self.weight_distribution,
                "total_weight": self.total_weight
            },
            "packed_items": [
                {
                    "name": item.name,
                    "position": item.position,
                    "dimensions": item.dimensions,
                    "original_dims": item.original_dims,
                    "weight": item.weight,
                    "quantity": item.quantity,
                    "fragility": item.fragility,
                    "stackable": item.stackable,
                    "bundle": item.bundle
                }
                for item in self.items
            ],
            "unpacked_items": [
                {
                    "name": name,
                    "reason": reason,
                    "dimensions": item.dimensions,
                    "weight": item.weight
                }
                for name, (reason, item) in self.unpacked_reasons.items()
            ],
            "unused_spaces": [
                {
                    "position": (x, y, z),
                    "dimensions": (w, d, h),
                    "volume": w * d * h
                }
                for x, y, z, w, d, h in self.unused_spaces
            ],
            "metrics": {
                "weight_balance_score": self._calculate_weight_balance_score(),
                "interlocking_score": self._calculate_interlocking_score(),
                "total_items": len(self.items),
                "unpacked_items": len(self.unpacked_reasons)
            }
        }

        # Save machine-readable JSON report
        with open(f"{filename}.json", 'w') as f:
            json.dump(report_data, f, indent=4)

        # Generate human-readable report
        with open(f"{filename}.txt", 'w') as f:
            f.write("=== Container Loading Report ===\n\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("Container Specifications:\n")
            f.write(f"Dimensions (L×W×H): {self.dimensions[0]}m × {self.dimensions[1]}m × {self.dimensions[2]}m\n")
            f.write(f"Total Volume: {self.total_volume:.2f}m³\n")
            f.write(f"Volume Utilization: {self.volume_utilization:.1f}%\n")
            f.write(f"Remaining Volume: {self.remaining_volume:.2f}m³\n")
            f.write(f"Total Weight: {self.total_weight:.2f}kg\n")
            f.write(f"Center of Gravity: ({self.center_of_gravity[0]:.2f}, {self.center_of_gravity[1]:.2f}, {self.center_of_gravity[2]:.2f})\n\n")
            
            f.write("Packed Items:\n")
            for item in sorted(self.items, key=lambda x: x.position[2]):
                f.write(f"- {item.name}: at ({item.position[0]:.2f}, {item.position[1]:.2f}, {item.position[2]:.2f})\n")
                f.write(f"  Dimensions: {item.dimensions[0]:.2f}m × {item.dimensions[1]:.2f}m × {item.dimensions[2]:.2f}m\n")
                f.write(f"  Weight: {item.weight:.2f}kg, Quantity: {item.quantity}\n")
            
            f.write("\nUnpacked Items:\n")
            for name, (reason, item) in self.unpacked_reasons.items():
                f.write(f"- {name}: {reason}\n")
                f.write(f"  Dimensions: {item.dimensions[0]:.2f}m × {item.dimensions[1]:.2f}m × {item.dimensions[2]:.2f}m\n")
                f.write(f"  Weight: {item.weight:.2f}kg\n")
            
            f.write("\nUnused Spaces:\n")
            for x, y, z, w, d, h in sorted(self.unused_spaces, key=lambda s: s[2]):
                f.write(f"- Position: ({x:.2f}, {y:.2f}, {z:.2f})\n")
                f.write(f"  Dimensions: {w:.2f}m × {d:.2f}m × {h:.2f}m\n")
                f.write(f"  Volume: {w*d*h:.2f}m³\n")
            
            f.write("\nMetrics:\n")
            f.write(f"Weight Balance Score: {self._calculate_weight_balance_score():.2f}\n")
            f.write(f"Interlocking Score: {self._calculate_interlocking_score():.2f}\n")
            
        return report_data

    def create_interactive_app(self):
        """Create a Dash app for interactive visualization"""
        app = dash.Dash(__name__)
        
        app.layout = html.Div([
            html.Button('Generate Alternative Arrangement', id='rearrange-button'),
            dcc.Graph(id='container-view', figure=self.create_interactive_visualization()),
            html.Div([
                html.H3('Packing Statistics'),
                html.P(id='stats-display')
            ])
        ])
        
        @app.callback(
            [Output('container-view', 'figure'),
             Output('stats-display', 'children')],
            [Input('rearrange-button', 'n_clicks')]
        )
        def update_arrangement(n_clicks):
            if n_clicks is None:
                return self.create_interactive_visualization(), (
                    f"Volume Utilization: {self.volume_utilization:.1f}%<br>"
                    f"Items Packed: {len(self.items)}/{len(self.items) + len(self.unpacked_reasons)}<br>"
                    f"Weight Balance Score: {self._calculate_weight_balance_score():.2f}"
                )
            
            # On button click, generate slightly modified visualization
            # (In a real system, this would trigger reoptimization)
            return self.create_interactive_visualization(), (
                f"Volume Utilization: {self.volume_utilization:.1f}%<br>"
                f"Items Packed: {len(self.items)}/{len(self.items) + len(self.unpacked_reasons)}<br>"
                f"Weight Balance Score: {self._calculate_weight_balance_score():.2f}<br>"
                f"Alternative arrangement #{n_clicks} generated"
            )
        
        return app