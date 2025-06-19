#!/usr/bin/env python3
"""
Test script for production deployment
Run this script to verify your application is properly configured for production
"""
import os
import sys
import subprocess
import tempfile

def test_imports():
    """Test that all imports work correctly"""
    print("Testing imports...")
    try:
        # Test main application import
        from app_modular import create_app, AppConfig
        print("[OK] Main application imports successful")
        
        # Test configuration
        from config import UPLOAD_FOLDER, PLANS_FOLDER, SECRET_KEY
        print("[OK] Configuration imports successful")
        
        # Test handlers
        from modules.handlers import bp
        print("[OK] Handler imports successful")
        
        return True
    except ImportError as e:
        print(f"[ERROR] Import error: {e}")
        return False

def test_app_creation():
    """Test that the Flask app can be created"""
    print("\nTesting app creation...")
    try:
        from app_modular import create_app
        app = create_app()
        print("[OK] Flask app created successfully")
        return True
    except Exception as e:
        print(f"[ERROR] App creation failed: {e}")
        return False

def test_environment_config():
    """Test environment configuration"""
    print("\nTesting environment configuration...")
    
    # Test production mode
    original_env = os.environ.get('FLASK_ENV')
    os.environ['FLASK_ENV'] = 'production'
    
    try:
        from app_modular import AppConfig
        
        if AppConfig.is_production():
            print("[OK] Production mode detection works")
        else:
            print("[ERROR] Production mode detection failed")
            return False
            
        # Test port configuration
        os.environ['PORT'] = '8080'
        expected_port = 8080
        actual_port = AppConfig.get_port()
        
        if actual_port == expected_port:
            print("[OK] Port configuration from environment works")
        else:
            print(f"[ERROR] Port configuration failed: expected {expected_port}, got {actual_port}")
            return False
            
        return True
    except Exception as e:
        print(f"[ERROR] Environment configuration test failed: {e}")
        return False
    finally:
        # Restore original environment
        if original_env:
            os.environ['FLASK_ENV'] = original_env
        else:
            os.environ.pop('FLASK_ENV', None)
        os.environ.pop('PORT', None)

def test_wsgi_entry():
    """Test WSGI entry point"""
    print("\nTesting WSGI entry point...")
    try:
        import wsgi
        if hasattr(wsgi, 'app'):
            print("[OK] WSGI entry point works")
            return True
        else:
            print("[ERROR] WSGI entry point missing 'app' attribute")
            return False
    except Exception as e:
        print(f"❌ WSGI entry point test failed: {e}")
        return False

def test_requirements():
    """Test that all required packages are installed"""
    print("\nTesting requirements...")
    
    required_packages = [
        'flask',
        'flask_socketio',
        'numpy',
        'pandas',
        'requests',
        'psutil'
    ]
    
    failed_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            failed_packages.append(package)
    
    if failed_packages:
        print(f"\n❌ Missing packages: {', '.join(failed_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def test_gunicorn():
    """Test that gunicorn can be used"""
    print("\nTesting gunicorn compatibility...")
    try:
        import gunicorn
        print("✅ Gunicorn is installed")
        
        # Test that the WSGI app can be loaded by gunicorn
        result = subprocess.run([
            sys.executable, '-c',
            'import wsgi; print("WSGI app loaded:", type(wsgi.app))'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ WSGI app can be loaded by gunicorn")
            return True
        else:
            print(f"❌ WSGI app loading failed: {result.stderr}")
            return False
            
    except ImportError:
        print("❌ Gunicorn not installed")
        print("Run: pip install gunicorn")
        return False
    except Exception as e:
        print(f"❌ Gunicorn test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Production Deployment Test ===\n")
    
    tests = [
        test_requirements,
        test_imports,
        test_app_creation,
        test_environment_config,
        test_wsgi_entry,
        test_gunicorn
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print("=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Your application is ready for deployment.")
        return 0
    else:
        print("❌ Some tests failed. Please fix the issues before deploying.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
