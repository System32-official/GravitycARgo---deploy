#!/usr/bin/env python3
"""
Render Deployment Debugging Script
This script helps diagnose issues with the AR server when deployed on Render
"""

import os
import requests
import json

def test_render_deployment():
    """Test the deployed application on Render"""
    print("🔍 Render Deployment Debug Tool")
    print("=" * 50)
    
    # Get the deployment URL (you'll need to set this)
    render_url = input("Enter your Render app URL (e.g., https://your-app.onrender.com): ").strip()
    
    if not render_url:
        print("❌ No URL provided. Please provide your Render app URL.")
        return
    
    if not render_url.startswith(('http://', 'https://')):
        render_url = f"https://{render_url}"
    
    print(f"\n🌐 Testing deployment at: {render_url}")
    
    # Test 1: Health check
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{render_url}/health", timeout=10)
        if response.status_code == 200:
            print("   ✅ Health check passed")
            health_data = response.json()
            print(f"   Environment: {health_data.get('environment')}")
            print(f"   Version: {health_data.get('version')}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False
    
    # Test 2: Server config
    print("\n2. Testing server configuration...")
    try:
        response = requests.get(f"{render_url}/api/server-config", timeout=10)
        if response.status_code == 200:
            print("   ✅ Server config accessible")
            config = response.json()
            print(f"   Base URL: {config.get('base_url')}")
            print(f"   Is Production: {config.get('is_production')}")
            print(f"   Environment: {config.get('environment')}")
        else:
            print(f"   ❌ Server config failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Server config error: {e}")
    
    # Test 3: JSON server status
    print("\n3. Testing JSON server status...")
    try:
        response = requests.get(f"{render_url}/check_json_server_status", timeout=10)
        if response.status_code == 200:
            print("   ✅ JSON server status accessible")
            status = response.json()
            print(f"   Running: {status.get('running')}")
            if status.get('url'):
                print(f"   URL: {status.get('url')}")
        else:
            print(f"   ❌ JSON server status failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ JSON server status error: {e}")
    
    # Test 4: Start JSON server
    print("\n4. Testing JSON server start...")
    try:
        response = requests.post(f"{render_url}/start_json_server", timeout=15)
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("   ✅ JSON server started successfully")
                print(f"   AR URL: {result.get('url')}")
                
                # Test 5: Access the JSON data
                print("\n5. Testing JSON data access...")
                try:
                    data_response = requests.get(result.get('url'), timeout=10)
                    if data_response.status_code == 200:
                        print("   ✅ JSON data accessible")
                        data = data_response.json()
                        print(f"   Container dimensions: {data.get('container_dimensions', 'Unknown')}")
                        boxes = data.get('boxes', [])
                        print(f"   Number of boxes: {len(boxes)}")
                    else:
                        print(f"   ❌ JSON data access failed: {data_response.status_code}")
                except Exception as e:
                    print(f"   ❌ JSON data access error: {e}")
                    
            else:
                print(f"   ❌ JSON server start failed: {result.get('error')}")
        else:
            print(f"   ❌ JSON server start request failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   ❌ JSON server start error: {e}")
    
    print("\n" + "=" * 50)
    print("🔧 TROUBLESHOOTING TIPS:")
    print("1. Make sure your Render service is running")
    print("2. Check Render logs for any startup errors")
    print("3. Verify environment variables are set correctly")
    print("4. Ensure container_plans directory exists with JSON files")
    print("5. Check if any browser extensions are blocking requests")
    print("\n📋 If AR View still doesn't work:")
    print(f"   - Try opening: {render_url}")
    print("   - Check browser console for errors")
    print("   - Disable ad blockers temporarily")
    print("   - Try in incognito/private mode")

def create_environment_setup():
    """Create environment variable setup for Render"""
    print("\n🔧 RENDER ENVIRONMENT SETUP")
    print("=" * 40)
    print("Add these environment variables in your Render dashboard:")
    print()
    print("Key: FLASK_ENV")
    print("Value: production")
    print()
    print("Key: DEBUG") 
    print("Value: False")
    print()
    print("Key: JSON_SERVER_PORT")
    print("Value: 8000")
    print()
    print("Optional - if you want to set a custom service name:")
    print("Key: RENDER_SERVICE_NAME")
    print("Value: your-app-name")

if __name__ == "__main__":
    try:
        test_render_deployment()
        create_environment_setup()
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
