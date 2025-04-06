"""
Utility functions for container packing
"""
from optigenix_module.constants import TRANSPORT_MODES, CONTAINER_TYPES

def get_transport_config():
    """Interactive function to select transport mode and container type"""
    print("\n=== Transport Mode Selection ===")
    for key, (mode, _) in TRANSPORT_MODES.items():
        print(f"{key}. {mode}")
    
    while True:
        mode_choice = input("\nSelect transport mode (1-5): ")
        if mode_choice in TRANSPORT_MODES:
            break
        print("Invalid choice. Please try again.")
    
    mode_name, container_options = TRANSPORT_MODES[mode_choice]
    
    if mode_choice == '5':
        # Custom dimensions
        print("\nEnter custom container dimensions (in meters):")
        length = float(input("Length: "))
        width = float(input("Width: "))
        height = float(input("Height: "))
        return (length, width, height)
    else:
        print(f"\nAvailable {mode_name} container types:")
        print("\nID | Type | Dimensions (L × W × H)")
        print("-" * 50)
        for i, container in enumerate(container_options, 1):
            dims = CONTAINER_TYPES[container]
            print(f"{i:2d} | {container:20s} | {dims[0]:.2f}m × {dims[1]:.2f}m × {dims[2]:.2f}m")
        
        while True:
            try:
                choice = int(input(f"\nSelect container type (1-{len(container_options)}): "))
                if 1 <= choice <= len(container_options):
                    return CONTAINER_TYPES[container_options[choice-1]]
            except ValueError:
                pass
            print("Invalid choice. Please try again.")

def can_interlock(item1, item2) -> bool:
    """Check if two items can potentially interlock"""
    if not (item1 and item2):
        return False
        
    try:
        dims1 = item1.dimensions
        dims2 = item2.dimensions
        
        # Check if any dimension pairs are similar (within 10%)
        for d1 in dims1:
            for d2 in dims2:
                if abs(d1 - d2) / max(d1, d2) < 0.1:
                    return True
                    
        # Check if items can stack
        if item1.stackable == 'YES' and item2.stackable == 'YES':
            return True
            
        return False
        
    except Exception:
        return False