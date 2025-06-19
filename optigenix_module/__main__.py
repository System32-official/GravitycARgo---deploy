"""
Main entry point for the container packing application
"""
import os
import sys
import traceback
from typing import List

from optigenix_module.models.container import EnhancedContainer
from optigenix_module.models.item import Item
from optigenix_module.optimization.genetic import optimize_packing_with_genetic_algorithm
from optigenix_module.utils import get_transport_config

def parse_items_from_input():
    """Parse item data from user input"""
    print("\n=== Item Entry ===")
    print("Enter items to pack (name, length, width, height, weight, quantity, fragility, stackable, bundle)")
    print("Enter blank line when finished")
    
    items = []
    item_num = 1
    
    while True:
        try:
            print(f"\nItem #{item_num}")
            name = input("Name: ")
            if not name:
                break
                
            length = float(input("Length (m): "))
            width = float(input("Width (m): "))
            height = float(input("Height (m): "))
            weight = float(input("Weight (kg): "))
            
            quantity = int(input("Quantity: "))
            
            fragility = ""
            while fragility not in ["LOW", "MEDIUM", "HIGH"]:
                fragility = input("Fragility (LOW, MEDIUM, HIGH): ").upper()
                
            stackable = ""
            while stackable not in ["YES", "NO"]:
                stackable = input("Stackable (YES, NO): ").upper()
                
            boxing_type = input("Boxing Type (default: STANDARD): ").upper() or "STANDARD"
            
            bundle = ""
            while bundle not in ["YES", "NO"]:
                bundle = input("Bundle items (YES, NO): ").upper()
                
            item = Item(name, length, width, height, weight, quantity, 
                      fragility, stackable, boxing_type, bundle)
            items.append(item)
            item_num += 1
            
        except ValueError as e:
            print(f"Error: {e}. Please try again.")
            
    return items

def main():
    """Main program execution"""
    print("=== 3D Container Loading Optimizer with Genetic Algorithm ===")
    
    try:
        # Get container dimensions
        container_dims = get_transport_config()
        
        # Get items from user input
        items = parse_items_from_input()
        
        if not items:
            print("No items entered. Exiting.")
            return
              # Run genetic algorithm packing with user input for parameters
        print("\nOptimizing container packing with genetic algorithm...")
        population_size = int(input("Enter population size: "))
        generations = int(input("Enter number of generations: "))
        container = optimize_packing_with_genetic_algorithm(
            items, container_dims, population_size=population_size, generations=generations
        )
        
        # Generate visualization
        print("\nGenerating visualization...")
        fig = container.create_interactive_visualization()
        fig.show()
        
        # Generate report
        report_file = input("\nEnter filename for packing report (or press Enter for default): ")
        if not report_file:
            report_file = "packing_report"
            
        container.generate_packing_report(report_file)
        print(f"\nReport saved as {report_file}.json and {report_file}.txt")
        
        # Create interactive app if requested
        create_app = input("\nCreate interactive visualization app? (y/n): ")
        if create_app.lower() == 'y':
            app = container.create_interactive_app()
            app.run_server(debug=True)
            
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()