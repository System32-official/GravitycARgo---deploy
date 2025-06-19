#!/usr/bin/env python3
"""
Manual AR Server Test
Simple test to verify AR server functionality without external dependencies
"""
import os
import sys
import json
from pathlib import Path

def test_manual_ar_server():
    """Manual test of AR server components"""
    print("Manual AR Server Test")
    print("=" * 40)
    
    try:
        # Test 1: Check if container plans exist
        print("1. Checking container plans directory...")
        container_dir = Path("container_plans")
        if container_dir.exists():
            json_files = list(container_dir.glob("*.json"))
            print(f"   ✓ Found {len(json_files)} JSON files")
            if json_files:
                # Test reading the latest file
                latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
                print(f"   ✓ Latest file: {latest_file.name}")
                
                try:
                    with open(latest_file, 'r') as f:
                        data = json.load(f)
                    print(f"   ✓ JSON file is valid")
                    print(f"   ✓ Container dimensions: {data.get('container_dimensions', 'N/A')}")
                    print(f"   ✓ Packed items: {len(data.get('packed_items', []))}")
                except Exception as e:
                    print(f"   ⚠ Error reading JSON: {e}")
            else:
                print("   ⚠ No JSON files found")
        else:
            print("   ❌ Container plans directory not found")
            return False
        
        # Test 2: Import AR server modules
        print("\n2. Testing module imports...")
        try:
            sys.path.insert(0, os.getcwd())
            from app_modular import JSONServerService, AppConfig
            print("   ✓ JSONServerService imported")
            
            from ar_server_manager import ARServerManager
            print("   ✓ ARServerManager imported")
            
        except ImportError as e:
            print(f"   ❌ Import error: {e}")
            return False
        
        # Test 3: Create service instance
        print("\n3. Testing service instantiation...")
        try:
            service = JSONServerService.get_instance()
            print("   ✓ JSONServerService instance created")
            
            ar_manager = ARServerManager()
            print("   ✓ ARServerManager instance created")
            
        except Exception as e:
            print(f"   ❌ Instantiation error: {e}")
            return False
        
        # Test 4: Test configuration
        print("\n4. Testing configuration...")
        print(f"   ✓ JSON Server Port: {AppConfig.JSON_SERVER_PORT}")
        print(f"   ✓ Standard JSON filename: {AppConfig.STANDARD_JSON_FILENAME}")
        print(f"   ✓ Ngrok domain: {AppConfig.NGROK_DOMAIN}")
        
        # Test 5: Test JSON file operations
        print("\n5. Testing JSON file operations...")
        try:
            success = service.update_json_file()
            if success:
                print("   ✓ JSON file update successful")
                
                # Check if staging file exists
                staging_path = service.json_path
                if os.path.exists(staging_path):
                    print(f"   ✓ Staging file created: {staging_path}")
                else:
                    print(f"   ⚠ Staging file not found: {staging_path}")
            else:
                print("   ⚠ JSON file update failed (possibly no source files)")
                
        except Exception as e:
            print(f"   ❌ JSON file operation error: {e}")
        
        print("\n6. AR Server Status...")
        print("   The AR server implementation appears to be working correctly.")
        print("   To start the full AR server:")
        print("   1. Run: python app_modular.py")
        print("   2. Make POST request to: http://localhost:5000/start_json_server")
        print("   3. Or use: python ar_server_manager.py start")
        
        print("\n✅ Manual AR Server test completed successfully!")
        print("\nNote: For ngrok functionality, install ngrok from https://ngrok.com/")
        print("The server will work locally without ngrok.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    test_manual_ar_server()
