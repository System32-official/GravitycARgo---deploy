#!/usr/bin/env python3
"""
Quick deployment readiness test
"""
import os
import sys

# Set production environment
os.environ['FLASK_ENV'] = 'production'
os.environ['DEBUG'] = 'False'

print("=== Quick Deployment Test ===")

try:
    print("1. Testing LLM connector import...")
    from optigenix_module.utils.llm_connector import get_llm_client
    print("   ✓ LLM connector imported successfully")
    
    print("2. Testing app import...")
    from app_modular import create_app
    print("   ✓ App factory imported successfully")
    
    print("3. Testing WSGI import...")
    import wsgi
    print("   ✓ WSGI module imported successfully")
    
    print("4. Creating app instance...")
    app = create_app()
    print("   ✓ App created successfully")
    
    print("\n=== All Tests Passed ===")
    print("✓ Application is ready for deployment!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)
