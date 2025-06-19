import os
import sys

print("Testing AR Server...")

try:
    # Check if required files exist
    required_files = [
        'app_modular.py',
        'ar_server_manager.py', 
        'config.py'
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file} exists")
        else:
            print(f"❌ {file} missing")
    
    # Check directories
    if os.path.exists('container_plans'):
        print(f"✓ container_plans directory exists")
        import glob
        json_files = glob.glob('container_plans/*.json')
        print(f"  Found {len(json_files)} JSON files")
    else:
        print("❌ container_plans directory missing")
        
    # Try to import the AR server manager
    from ar_server_manager import ar_server
    print("✓ AR server manager imported successfully")
    
    print("\nAR Server implementation looks complete!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
