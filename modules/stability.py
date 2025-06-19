"""
Stability analysis functions for the container packing application
"""
import numpy as np
from modules.utils import calculate_overlap_area, check_overlap_2d

def analyze_layer_distribution(container):
    """Analyze how items are distributed in layers"""
    layers = {}
    for item in container.items:
        layer_height = round(item.position[2], 2)
        if layer_height not in layers:
            layers[layer_height] = []
        layers[layer_height].append(item)
    return layers

def analyze_stability(container):
    """Analyze stability of packed items"""
    stability_report = {
        "item_stability": {},
        "overall_stability": 0,
        "critical_points": []
    }
    
    for item in container.items:
        support_score = calculate_support_score(container, item)
        cog_impact = calculate_cog_impact(container, item)
        interlocking = calculate_item_interlocking(container, item)
        
        stability_report["item_stability"][item.name] = {
            "support_score": f"{support_score:.2f}",
            "cog_impact": f"{cog_impact:.2f}",
            "interlocking": f"{interlocking:.2f}",
            "overall": f"{(support_score + cog_impact + interlocking) / 3:.2f}"
        }
        
        if support_score < 0.5 or cog_impact < 0.5:
            stability_report["critical_points"].append({
                "item": item.name,
                "position": [f"{x:.2f}" for x in item.position],
                "issue": "Low stability score"
            })
    
    if container.items:
        stability_report["overall_stability"] = f"{sum(float(x['overall']) for x in stability_report['item_stability'].values()) / len(container.items):.2f}"
    else:
        stability_report["overall_stability"] = "0.00"
    
    return stability_report

def calculate_support_score(container, item):
    """Calculate how well an item is supported"""
    x, y, z = item.position
    w, d, h = item.dimensions
    
    if z == 0:  # On the ground
        return 1.0
        
    support_area = 0
    total_area = w * d
    
    for other in container.items:
        if other == item:
            continue
            
        if abs(other.position[2] + other.dimensions[2] - z) < 0.001:
            overlap = calculate_overlap_area(
                (x, y, w, d),
                (other.position[0], other.position[1], 
                 other.dimensions[0], other.dimensions[1])
            )
            support_area += overlap
            
    return min(support_area / total_area, 1.0)

def calculate_cog_impact(container, item):
    """Calculate impact on center of gravity"""
    ideal_cog = np.array(container.dimensions) / 2
    current_cog = np.array(container.center_of_gravity)
    item_cog = np.array(item.position) + np.array(item.dimensions) / 2
    
    current_dist = np.linalg.norm(current_cog - ideal_cog)
    item_dist = np.linalg.norm(item_cog - ideal_cog)
    
    return 1.0 / (1.0 + abs(item_dist - current_dist))

def calculate_item_interlocking(container, item):
    """Calculate how well item interlocks with others"""
    contact_count = 0
    max_contacts = 6  # Maximum possible contacts (6 faces)
    
    for other in container.items:
        if other == item:
            continue
            
        if has_surface_contact(item.position, item.dimensions, other):
            contact_count += 1
            
    return contact_count / max_contacts

def has_surface_contact(pos1, dims1, item2):
    """Check if two items have surface contact"""
    if not item2.position:
        return False
        
    x1, y1, z1 = pos1
    l1, w1, h1 = dims1
    x2, y2, z2 = item2.position
    l2, w2, h2 = item2.dimensions
    
    # Check for surface contact with tolerance
    tolerance = 0.001
    
    # Bottom face contact
    if abs(z1 - (z2 + h2)) < tolerance:
        if check_overlap_2d(
            (x1, y1, l1, w1),
            (x2, y2, l2, w2)
        ):
            return True
            
    # Top face contact
    if abs((z1 + h1) - z2) < tolerance:
        if check_overlap_2d(
            (x1, y1, l1, w1),
            (x2, y2, l2, w2)
        ):
            return True
            
    # Front/back face contacts
    if abs(y1 - (y2 + w2)) < tolerance or abs((y1 + w1) - y2) < tolerance:
        if check_overlap_2d(
            (x1, z1, l1, h1),
            (x2, z2, l2, h2)
        ):
            return True
            
    # Left/right face contacts
    if abs(x1 - (x2 + l2)) < tolerance or abs((x1 + l1) - x2) < tolerance:
        if check_overlap_2d(
            (y1, z1, w1, h1),
            (y2, z2, w2, h2)
        ):
            return True
            
    return False

"""Converted to use utility function - contents moved to utils.py"""