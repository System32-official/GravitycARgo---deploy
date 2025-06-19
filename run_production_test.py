#!/usr/bin/env python3
"""
Local production test script
Test your application locally with production settings before deploying to Render
"""
import os
import sys
import subprocess
import time
import signal
import webbrowser
from threading import Timer

def setup_production_env():
    """Set up production environment variables"""
    print("Setting up production environment...")
    
    # Set production environment variables
    os.environ['FLASK_ENV'] = 'production'
    os.environ['DEBUG'] = 'False'
    os.environ['SECRET_KEY'] = 'test-production-key-change-for-real-deployment'
    os.environ['LOG_LEVEL'] = 'INFO'
    os.environ['PORT'] = '5000'
    
    print("✅ Production environment configured")

def run_production_server():
    """Run the application using gunicorn"""
    print("\nStarting application with gunicorn...")
    print("This simulates how your app will run on Render")
    
    cmd = [
        'gunicorn',
        '--bind', '0.0.0.0:5000',
        '--workers', '2',
        '--timeout', '300',
        '--access-logfile', '-',
        '--error-logfile', '-',
        'wsgi:app'
    ]
    
    try:
        print(f"Running: {' '.join(cmd)}")
        print("\n" + "="*50)
        print("🚀 Application starting...")
        print("📊 Dashboard: http://localhost:5000")
        print("🔗 API Health: http://localhost:5000/status")
        print("📋 Container Plans: http://localhost:5000/api/container_plan.json")
        print("="*50 + "\n")
        
        # Open browser after a delay
        def open_browser():
            try:
                webbrowser.open('http://localhost:5000')
            except:
                pass
        
        Timer(3.0, open_browser).start()
        
        # Run the server
        process = subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Server failed to start: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ gunicorn not found. Please install it:")
        print("pip install gunicorn")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False
    
    return True

def check_dependencies():
    """Check if all dependencies are installed"""
    print("Checking dependencies...")
    
    try:
        import gunicorn
        print("✅ gunicorn")
    except ImportError:
        print("❌ gunicorn - Run: pip install gunicorn")
        return False
    
    try:
        from wsgi import app
        print("✅ wsgi application")
    except ImportError as e:
        print(f"❌ wsgi application - {e}")
        return False
    
    return True

def main():
    """Main execution function"""
    print("=== Local Production Test ===\n")
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install missing packages.")
        return 1
    
    # Set up production environment
    setup_production_env()
    
    print("\n📝 Note: This test uses production settings but with a test SECRET_KEY")
    print("🔒 For real deployment, use Render's auto-generated SECRET_KEY")
    
    # Run the production server
    print("\nPress Ctrl+C to stop the server")
    input("Press Enter to start the production server...")
    
    success = run_production_server()
    
    if success:
        print("\n✅ Production test completed successfully!")
        print("🚀 Your application is ready for Render deployment")
    else:
        print("\n❌ Production test failed")
        print("🔧 Please fix the issues before deploying")
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
