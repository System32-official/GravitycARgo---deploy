#!/usr/bin/env python3

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ar_server():
    """Test AR server functionality"""
    print("=" * 50)
    print("Testing AR Server Implementation")
    print("=" * 50)
    
    try:
        # Test imports
        print("1. Testing imports...")
        from app_modular import JSONServerService, AppConfig
        print("   ✓ Successfully imported JSONServerService and AppConfig")
        
        # Test service creation
        print("\n2. Testing service creation...")
        service = JSONServerService.get_instance()
        print("   ✓ Successfully created JSONServerService instance")
        
        # Check directories
        print("\n3. Checking directories...")
        print(f"   Data dir: {service.data_dir}")
        print(f"   Data dir exists: {os.path.exists(service.data_dir)}")
        print(f"   Staging dir: {service.staging_dir}")
        print(f"   Staging dir exists: {os.path.exists(service.staging_dir)}")
        
        # Check for JSON files
        print("\n4. Checking for container plan files...")
        import glob
        json_files = glob.glob(os.path.join(service.data_dir, "*.json"))
        print(f"   Found {len(json_files)} JSON files")
        
        if json_files:
            latest_file = max(json_files, key=os.path.getmtime)
            print(f"   Latest file: {os.path.basename(latest_file)}")
            
            # Test file update
            print("\n5. Testing JSON file update...")
            result = service.update_json_file()
            print(f"   Update result: {result}")
            
            if result:
                print(f"   Staging file exists: {os.path.exists(service.json_path)}")
                
        else:
            print("   No JSON files found. Create a container plan first.")
            
        # Test port checking
        print("\n6. Testing port availability...")
        port_in_use = service.is_port_in_use(AppConfig.JSON_SERVER_PORT)
        print(f"   Port {AppConfig.JSON_SERVER_PORT} in use: {port_in_use}")
        
        if port_in_use:
            alt_port = service.find_available_port(AppConfig.JSON_SERVER_PORT + 1)
            print(f"   Alternative port: {alt_port}")
            
        print("\n7. Testing server start (dry run)...")
        print(f"   Production mode: {AppConfig.is_production()}")
        print(f"   Server URL would be: {service.get_url()}")
        
        print("\n" + "=" * 50)
        print("✓ AR Server tests completed successfully!")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_ar_server()
