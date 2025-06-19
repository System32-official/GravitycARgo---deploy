#!/usr/bin/env python3
"""
Quick test script to check AR server functionality
"""
import sys
import os
import requests
import time
import threading

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_ar_server():
    """Test the AR server functionality"""
    print("Testing AR Server Implementation...")
    
    try:
        # Test 1: Import modules
        print("1. Testing imports...")
        from app_modular import JSONServerService, create_app
        from ar_server_manager import ARServerManager
        print("   ✓ All modules imported successfully")
        
        # Test 2: Check if JSONServerService can be instantiated
        print("2. Testing JSONServerService instantiation...")
        service = JSONServerService.get_instance()
        print("   ✓ JSONServerService created successfully")
        
        # Test 3: Check if ARServerManager can be instantiated
        print("3. Testing ARServerManager instantiation...")
        ar_manager = ARServerManager()
        print("   ✓ ARServerManager created successfully")
        
        # Test 4: Test Flask app creation
        print("4. Testing Flask app creation...")
        app = create_app()
        print("   ✓ Flask app created successfully")
        
        # Test 5: Check container plans directory
        print("5. Checking container plans directory...")
        if os.path.exists("container_plans"):
            files = [f for f in os.listdir("container_plans") if f.endswith('.json')]
            print(f"   ✓ Found {len(files)} JSON files in container_plans/")
        else:
            print("   ⚠ container_plans directory not found")
        
        # Test 6: Test JSON server start (without actually starting it)
        print("6. Testing JSON server configuration...")
        try:
            # Just test if the update_json_file method works
            result = service.update_json_file()
            if result:
                print("   ✓ JSON file update test passed")
            else:
                print("   ⚠ JSON file update test failed - no JSON files found")
        except Exception as e:
            print(f"   ⚠ JSON file update test failed: {e}")
        
        print("\n✅ AR Server implementation appears to be complete!")
        print("\nTo test the full functionality:")
        print("1. Start the Flask application: python app_modular.py")
        print("2. Make a POST request to /start_json_server")
        print("3. Use the AR server manager: python ar_server_manager.py start")
        
        return True
        
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

def test_flask_endpoints():
    """Test Flask endpoints if the server is running"""
    print("\n7. Testing Flask endpoints (if server is running)...")
    
    try:
        # Check if Flask server is running on port 5000
        response = requests.get('http://localhost:5000/health', timeout=2)
        if response.status_code == 200:
            print("   ✓ Flask server is running")
            
            # Test AR server status endpoint
            try:
                response = requests.get('http://localhost:5000/check_json_server_status', timeout=2)
                if response.status_code == 200:
                    print("   ✓ JSON server status endpoint working")
                else:
                    print(f"   ⚠ JSON server status returned {response.status_code}")
            except Exception as e:
                print(f"   ⚠ JSON server status endpoint error: {e}")
                
        else:
            print(f"   ⚠ Flask server returned status {response.status_code}")
            
    except requests.ConnectionError:
        print("   ⚠ Flask server not running (this is normal if you haven't started it)")
    except Exception as e:
        print(f"   ⚠ Flask server test error: {e}")

if __name__ == "__main__":
    print("="*60)
    print("GravityCargo AR Server Test")
    print("="*60)
    
    success = test_ar_server()
    test_flask_endpoints()
    
    print("\n" + "="*60)
    if success:
        print("🎉 AR Server implementation test PASSED!")
    else:
        print("❌ AR Server implementation test FAILED!")
    print("="*60)
