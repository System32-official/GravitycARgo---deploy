"""
Report generation functions for the container packing application
"""
import pandas as pd
from modules.stability import analyze_layer_distribution, analyze_stability

def generate_detailed_report(container):
    """Generate a comprehensive packing report"""
    report = {
        "summary": {
            "container_dimensions": container.dimensions,
            "volume_utilization": f"{container.volume_utilization:.1f}%",
            "total_items_packed": len(container.items),
            "total_weight": f"{container.total_weight:.2f} kg",
            "remaining_volume": f"{container.remaining_volume:.2f} m³",
            "center_of_gravity": [f"{x:.2f}" for x in container.center_of_gravity],
            "weight_balance_score": f"{container._calculate_weight_balance_score():.2f}",
            "interlocking_score": f"{container._calculate_interlocking_score():.2f}"
        },
        "packed_items": [
            {
                "name": item.name,
                "position": [f"{x:.3f}" for x in item.position],
                "dimensions": [f"{x:.3f}" for x in item.dimensions],
                "weight": item.weight,
                "fragility": item.fragility,
                "load_bearing": item.stackable
            }
            for item in container.items
        ],
        "unpacked_items": [
            {
                "name": name,
                "reason": reason,
                "dimensions": [f"{x:.3f}" for x in item.dimensions],
                "weight": item.weight
            }
            for name, (reason, item) in container.unpacked_reasons.items()
        ],
        "placement_analysis": {
            "layer_distribution": analyze_layer_distribution(container),
            "weight_distribution": container.weight_distribution,
            "stability_analysis": analyze_stability(container)
        }
    }
    return report