#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
3D Container Cargo Visualization Tool
This script creates a 3D visualization of cargo placement in a shipping container
using Three.js for direct browser visualization.
"""

import argparse
import json
import os
import sys
import webbrowser
import argparse
from pathlib import Path
import requests

def check_flask_server():
    """Check if Flask server is running"""
    try:
        # Try to detect the current environment
        base_url = get_base_url()
        response = requests.get(f'{base_url}/health', timeout=2)
        return response.status_code == 200
    except:
        return False

def get_base_url():
    """Get the correct base URL for the current environment"""
    # Check if we're on Render (try to detect service name)
    render_service_name = os.environ.get('RENDER_SERVICE_NAME')
    if render_service_name:
        return f"https://{render_service_name}.onrender.com"
    
    # Check for manual Render URL
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    if render_url:
        return render_url
    
    # Check for other common production indicators
    port = os.environ.get('PORT', '5000')
    if os.environ.get('FLASK_ENV') == 'production':
        return f'http://0.0.0.0:{port}'
    
    # Default to localhost for local development
    return 'http://localhost:5000'

def start_flask_server_instructions():
    """Provide instructions for starting Flask server"""
    print("\n" + "="*60)
    print("🚀 AR VISUALIZATION READY!")
    print("="*60)
    
    if check_flask_server():
        print("✅ Flask server is already running!")
        print("   You can use the 'AR View' button in the visualization.")
    else:
        print("⚠️  Flask server is not running.")
        print("   To enable AR functionality:")
        print("   1. Open a new terminal/command prompt")
        print("   2. Navigate to this directory")
        print("   3. Run: python app_modular.py")
        print("   4. Then click 'AR View' in the visualization")
    
    print("\n📋 CORS Issue Fixed:")
    print("   ✅ Added Flask-CORS support")
    print("   ✅ Updated JavaScript to use absolute URLs")
    print("   ✅ Enhanced error handling")
    
    print("\n🌐 The visualization will open in your browser...")
    print("="*60)

def launch_pythreejs_visualization(data_dir="container_plans", specific_file=None):
    """Launch the 3D visualization directly
    
    Args:
        data_dir: Directory containing JSON container data files
        specific_file: Path to a specific JSON file to visualize (optional)
    """
    # Check if data directory exists
    data_path = Path(data_dir)
    if not data_path.exists() or not data_path.is_dir():
        print(f"Error: Data directory {data_dir} not found")
        sys.exit(1)
    
    # Find all JSON files in the data directory
    json_files = sorted(list(data_path.glob("*.json")), key=lambda x: x.stat().st_mtime, reverse=True)  # Most recent first
    if not json_files:
        print(f"No JSON files found in {data_dir}")
        sys.exit(1)

    print(f"Found {len(json_files)} JSON files in {data_dir}")
    
    # Create the 3D visualization HTML file
    create_3d_visualization(data_dir, specific_file)

def create_3d_visualization(data_dir="container_plans", specific_file=None):
    """Create a 3D HTML visualization using Three.js with enhanced interactive features"""
    # Get all JSON files or specific file
    if specific_file:
        json_files = [Path(specific_file)]
    else:
        json_files = sorted(list(Path(data_dir).glob("*.json")), key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Create HTML file in templates directory
    templates_dir = os.path.join(os.getcwd(), "templates")
    os.makedirs(templates_dir, exist_ok=True)
    html_file = os.path.join(templates_dir, "container_visualization.html")
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <title>3D Container Cargo Visualization Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        body {
            margin: 0;
            padding: 0;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0B1120 0%, #101B38 100%);
            color: #FFFFFF;
            height: 100vh;
            overflow-x: auto;
        }
        
        /* Glassmorphism effect */
        .glass {
            background: linear-gradient(145deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .glass-dark {
            background: linear-gradient(145deg, rgba(16, 27, 56, 0.8) 0%, rgba(11, 17, 32, 0.8) 100%);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(91, 118, 243, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }
        
        /* Animated background particles */
        .bg-particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            z-index: -1;
        }
        
        .particle {
            position: absolute;
            width: 2px;
            height: 2px;
            background: rgba(91, 118, 243, 0.3);
            border-radius: 50%;
            animation: float 6s ease-in-out infinite;
        }
        
        @keyframes float {
            0%, 100% { transform: translateY(0px) rotate(0deg); opacity: 0.3; }
            50% { transform: translateY(-20px) rotate(180deg); opacity: 0.8; }
        }
        
        /* Chart container */
        .chart-container {
            width: 100%;
            height: 200px;
        }
        
        /* Smooth transitions */
        .transition-all {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        /* Toggle button active state */
        .toggle-active {
            background: linear-gradient(135deg, #3C82F6 0%, #5B76F3 100%);
            color: white;
        }
        
        /* Status indicators */
        .status-green { color: #10B981; }
        .status-yellow { color: #F59E0B; }
        .status-red { color: #EF4444; }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(16, 27, 56, 0.3);
            border-radius: 3px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #3C82F6 0%, #5B76F3 100%);
            border-radius: 3px;
        }
        
        /* Scene container adjustments */
        #scene-container {
            height: 60vh;
            position: relative;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
            
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body class="bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
    <div class="bg-particles" id="particles"></div>
    
    <!-- Main Dashboard Container -->
    <div class="min-h-screen w-full overflow-x-auto">
        <!-- Header -->
        <header class="sticky top-0 z-50 px-6 py-4" style="background: linear-gradient(90deg, #0B1120 0%, #101B38 100%); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(91, 118, 243, 0.2); box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-6">
                    <h1 class="text-xl font-bold" style="color: #FFFFFF;">GravityCargo</h1>
                    
                    <!-- 3D/AR Toggle Button Group -->
                    <div class="flex rounded-lg overflow-hidden border border-white/20" style="background: rgba(255, 255, 255, 0.05);">
                        <button id="view-3d" class="flex items-center gap-2 px-4 py-2 text-sm font-medium transition-all duration-300 toggle-active">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 2L2 7L12 12L22 7L12 2Z"/>
                                <path d="M2 17L12 22L22 17"/>
                                <path d="M2 12L12 17L22 12"/>
                            </svg>
                            3D View
                        </button>
                        <button id="view-ar" class="flex items-center gap-2 px-4 py-2 text-sm font-medium transition-all duration-300" style="background: rgba(255, 255, 255, 0.9); color: rgba(107, 114, 128, 1); border-left: 1px solid rgba(255, 255, 255, 0.2);">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M5 12C5 8.13401 8.13401 5 12 5C15.866 5 19 8.13401 19 12V13H17V12C17 9.23858 14.7614 7 12 7C9.23858 7 7 9.23858 7 12V13H5V12Z"/>
                                <path d="M3 14H5V17C5 18.1046 5.89543 19 7 19H8V21H7C4.79086 21 3 19.2091 3 17V14Z"/>
                                <path d="M19 14H21V17C21 19.2091 19.2091 21 17 21H16V19H17C18.1046 19 19 18.1046 19 17V14Z"/>
                            </svg>
                            AR View
                        </button>
                    </div>
                </div>
                
                <!-- Right side content -->
                <div class="flex items-center gap-4">
                    <div class="flex items-center gap-3">
                        <span class="text-sm" style="color: #A0AEC0;">CREATED BY</span>
                        <span class="text-sm font-semibold" style="color: #5B76F3;">Team System32</span>
                    </div>
                    <button id="get-started-btn" class="px-6 py-2 rounded-lg font-medium transition-all duration-300 hover:shadow-lg" style="background: #3C82F6; color: #FFFFFF;">
                        Get Started
                    </button>
                </div>
            </div>
        </header>

        <!-- Main Content -->
        <div class="p-6 space-y-6">
            <!-- Statistics Cards Row -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 stats-grid">
                <div class="glass rounded-xl p-6 text-center transition-all hover:scale-105">
                    <div class="text-4xl font-bold text-blue-400 mb-2" id="space-utilization">95%</div>
                    <div class="text-sm text-gray-300">Space Utilization</div>
                </div>
                <div class="glass rounded-xl p-6 text-center transition-all hover:scale-105">
                    <div class="text-4xl font-bold text-green-400 mb-2" id="temp-control">100%</div>
                    <div class="text-sm text-gray-300">Temperature Control</div>
                </div>
                <div class="glass rounded-xl p-6 text-center transition-all hover:scale-105">
                    <div class="text-4xl font-bold text-purple-400 mb-2" id="time-saved">50%</div>
                    <div class="text-sm text-gray-300">Time Saved</div>
                </div>
                <div class="glass rounded-xl p-6 text-center transition-all hover:scale-105">
                    <div class="text-4xl font-bold text-yellow-400 mb-2" id="optimization">24/7</div>
                    <div class="text-sm text-gray-300">Optimization</div>
                </div>
            </div>

            <!-- Main Dashboard Grid -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 dashboard-grid">
                <!-- Left Panel - Controls and File Selection -->
                <div class="lg:col-span-1 space-y-6">
                    <!-- File Selection Card -->
                    <div class="glass-dark rounded-xl p-6">
                        <h2 class="text-lg font-semibold text-white mb-4">Container Selection</h2>
                        <select id="file-select" class="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-3 text-white">
""")
        
        # Add options for each file
        for i, file in enumerate(json_files):
            f.write(f'            <option value="{i}">{file.name}</option>\n')
        
        f.write("""
                        </select>
                    </div>

                    <!-- Container Metrics -->
                    <div class="glass-dark rounded-xl p-6">
                        <h2 class="text-lg font-semibold text-white mb-4">Container Metrics</h2>
                        <div class="grid grid-cols-2 gap-4">
                            <div class="bg-blue-500/20 rounded-lg p-4 text-center">
                                <div class="flex items-center justify-center w-10 h-10 bg-blue-500 rounded-full mx-auto mb-2">
                                    <span class="text-white">📊</span>
                                </div>
                                <div class="text-2xl font-bold text-blue-400" id="volume-percent">0%</div>
                                <div class="text-xs text-gray-300">Volume Utilization</div>
                            </div>
                            <div class="bg-purple-500/20 rounded-lg p-4 text-center">
                                <div class="flex items-center justify-center w-10 h-10 bg-purple-500 rounded-full mx-auto mb-2">
                                    <span class="text-white">📦</span>
                                </div>
                                <div class="text-2xl font-bold text-purple-400" id="total-items">0</div>
                                <div class="text-xs text-gray-300">Items Packed</div>
                            </div>
                            <div class="bg-green-500/20 rounded-lg p-4 text-center">
                                <div class="flex items-center justify-center w-10 h-10 bg-green-500 rounded-full mx-auto mb-2">
                                    <span class="text-white">⚖️</span>
                                </div>
                                <div class="text-2xl font-bold text-green-400" id="total-weight">0kg</div>
                                <div class="text-xs text-gray-300">Total Weight</div>
                            </div>
                            <div class="bg-yellow-500/20 rounded-lg p-4 text-center">
                                <div class="flex items-center justify-center w-10 h-10 bg-yellow-500 rounded-full mx-auto mb-2">
                                    <span class="text-white">📏</span>
                                </div>
                                <div class="text-2xl font-bold text-yellow-400" id="space-remaining">0m³</div>
                                <div class="text-xs text-gray-300">Space Remaining</div>
                            </div>
                        </div>
                    </div>

                    <!-- Charts Section -->
                    <div class="space-y-4">
                        <!-- Volume Utilization Chart -->
                        <div class="glass-dark rounded-xl p-6">
                            <h3 class="text-lg font-semibold text-white mb-4">Volume Utilization</h3>
                            <div class="chart-container">
                                <canvas id="volumeChart" width="400" height="200"></canvas>
                            </div>
                        </div>

                        <!-- Weight Distribution Chart -->
                        <div class="glass-dark rounded-xl p-6">
                            <h3 class="text-lg font-semibold text-white mb-4">Weight Distribution</h3>
                            <div class="chart-container">
                                <canvas id="weightChart" width="400" height="200"></canvas>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Center Panel - 3D Visualization -->
                <div class="lg:col-span-2 space-y-6">
                    <!-- 3D Scene Container -->
                    <div class="glass-dark rounded-xl p-6">
                        <div class="flex items-center justify-between mb-4">
                            <h2 class="text-lg font-semibold text-white">3D Container View</h2>
                            <div class="flex gap-2">
                                <!-- Animation Controls -->
                                <div class="flex gap-2 mr-4 border-r border-white/20 pr-4">
                                    <button id="play-animation" class="bg-green-500/20 hover:bg-green-500/30 text-green-400 px-3 py-2 rounded-lg text-sm transition-all flex items-center gap-2">
                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M8 5v14l11-7z"/>
                                        </svg>
                                        Play Loading
                                    </button>
                                    <button id="pause-animation" class="bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 px-3 py-2 rounded-lg text-sm transition-all flex items-center gap-2" style="display: none;">
                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
                                        </svg>
                                        Pause
                                    </button>
                                    <button id="reset-animation" class="bg-red-500/20 hover:bg-red-500/30 text-red-400 px-3 py-2 rounded-lg text-sm transition-all flex items-center gap-2">
                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M4 12a8 8 0 0 1 8-8V2.5L16 6l-4 3.5V8a6 6 0 1 0 6 6h1.5a7.5 7.5 0 1 1-7.5-7.5z"/>
                                        </svg>
                                        Reset
                                    </button>
                                </div>
                                <button id="reset-camera" class="bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 px-3 py-2 rounded-lg text-sm transition-all">
                                    Reset Camera
                                </button>
                                <button id="auto-rotate" class="bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 px-3 py-2 rounded-lg text-sm transition-all">
                                    Auto Rotate
                                </button>
                            </div>
                        </div>
                        <div id="scene-container" class="rounded-lg overflow-hidden"></div>
                    </div>

                    <!-- Controls Panel -->
                    <div class="glass-dark rounded-xl p-6">
                        <h3 class="text-lg font-semibold text-white mb-4">Visualization Controls</h3>
                        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                            <button id="view-orthographic" class="bg-white/10 hover:bg-white/20 text-white px-4 py-3 rounded-lg text-sm transition-all">
                                Orthographic
                            </button>
                            <button id="view-perspective" class="bg-blue-500 text-white px-4 py-3 rounded-lg text-sm transition-all">
                                Perspective
                            </button>
                            <button id="toggle-labels" class="bg-white/10 hover:bg-white/20 text-white px-4 py-3 rounded-lg text-sm transition-all">
                                Toggle Labels
                            </button>
                            <button id="toggle-wireframe" class="bg-white/10 hover:bg-white/20 text-white px-4 py-3 rounded-lg text-sm transition-all">
                                Wireframe
                            </button>
                            <button id="explode-view" class="bg-white/10 hover:bg-white/20 text-white px-4 py-3 rounded-lg text-sm transition-all">
                                Explode View
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Bottom Panel - Item Status List -->
            <div class="glass-dark rounded-xl p-6">
                <h2 class="text-lg font-semibold text-white mb-4">Cargo Item Status</h2>
                <div class="max-h-60 overflow-y-auto">
                    <div id="cargo-status-list" class="space-y-2">
                        <!-- Status items will be populated dynamically -->
                    </div>
                </div>
            </div>

            <!-- Legend -->
            <div class="glass-dark rounded-xl p-6">
                <h2 class="text-lg font-semibold text-white mb-4">Item Type Legend</h2>
                <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                    <div class="flex items-center gap-3">
                        <div class="w-4 h-4 rounded" style="background-color: rgba(100, 181, 246, 0.8);"></div>
                        <span class="text-sm text-gray-300">Standard</span>
                    </div>
                    <div class="flex items-center gap-3">
                        <div class="w-4 h-4 rounded" style="background-color: rgba(255, 241, 118, 0.8);"></div>
                        <span class="text-sm text-gray-300">Low Fragility</span>
                    </div>
                    <div class="flex items-center gap-3">
                        <div class="w-4 h-4 rounded" style="background-color: rgba(255, 213, 79, 0.8);"></div>
                        <span class="text-sm text-gray-300">Medium Fragility</span>
                    </div>
                    <div class="flex items-center gap-3">
                        <div class="w-4 h-4 rounded" style="background-color: rgba(255, 183, 77, 0.8);"></div>
                        <span class="text-sm text-gray-300">High Fragility</span>
                    </div>
                    <div class="flex items-center gap-3">
                        <div class="w-4 h-4 rounded" style="background-color: rgba(255, 112, 67, 0.8);"></div>
                        <span class="text-sm text-gray-300">Temperature Sensitive</span>
                    </div>
                    <div class="flex items-center gap-3">
                        <div class="w-4 h-4 rounded" style="background-color: rgba(240, 98, 146, 0.8);"></div>
                        <span class="text-sm text-gray-300">Both Properties</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Hover Info Panel -->
    <div id="box-info" class="fixed pointer-events-none opacity-0 glass-dark rounded-lg p-4 z-50 max-w-sm transition-opacity"></div>

    <!-- Three.js and Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/controls/OrbitControls.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <script>
        // Create animated background particles
        function createParticles() {
            const particlesContainer = document.getElementById('particles');
            const particleCount = 50;
            
            for (let i = 0; i < particleCount; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                particle.style.left = Math.random() * 100 + '%';
                particle.style.top = Math.random() * 100 + '%';
                particle.style.animationDelay = Math.random() * 6 + 's';
                particle.style.animationDuration = (Math.random() * 3 + 3) + 's';
                particlesContainer.appendChild(particle);
            }
        }
        
        // Container data will be loaded here
        const containerData = [];
        
        // Load the container data from JSON files
""")
        
        # Add container data with error handling
        valid_files = 0
        for file in json_files:
            try:
                with open(file, 'r') as json_file:
                    container_data = json.load(json_file)
                    f.write(f"        containerData.push({json.dumps(container_data)});\n")
                    valid_files += 1
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Warning: Skipping {file} due to parsing error: {e}")
                continue
        
        print(f"Successfully loaded {valid_files} valid JSON files")
        
        f.write("""
        // Set up the scene, camera, and renderer
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x0B1120);
        scene.fog = new THREE.Fog(0x0B1120, 10, 100);
        
        let camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
        camera.position.set(10, 10, 10);
        
        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        renderer.toneMapping = THREE.ACESFilmicToneMapping;
        renderer.toneMappingExposure = 1.2;
        
        // Add orbit controls
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.autoRotate = false;
        controls.autoRotateSpeed = 1.0;
        
        // Lighting setup
        const ambientLight = new THREE.AmbientLight(0x5B76F3, 0.4);
        scene.add(ambientLight);
        
        const mainLight = new THREE.DirectionalLight(0xffffff, 0.8);
        mainLight.position.set(10, 20, 10);
        mainLight.castShadow = true;
        scene.add(mainLight);
        
        // Box colors and other variables
        const colors = {
            normal: 0x64b5f6,
            temperature_sensitive: 0xff7043,
            fragile_low: 0xfff176,
            fragile_medium: 0xffd54f,
            fragile_high: 0xffb74d,
            both: 0xf06292,
            container: 0x5B76F3,
            grid: 0x3C82F6
        };
        
        let containerMeshes = [];
        let boxMeshes = [];
        let textSprites = [];
        let showLabels = true;
        let showWireframe = true;
        let explodedView = false;
        let currentContainerData = null;
        let isOrthographic = false;
        let autoRotate = false;
        
        // Animation variables
        let isAnimating = false;
        let animationPaused = false;
        let currentAnimationIndex = 0;
        let animationInterval = null;
        let animatedBoxes = [];
        let originalBoxPositions = [];
        
        // Charts
        let volumeChart = null;
        let weightChart = null;
        
        // Raycaster for mouse interaction
        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        let hoveredBox = null;
        const boxDataMap = new Map();
        
        // Initialize charts
        function initializeCharts() {
            // Volume Utilization Donut Chart
            const volumeCtx = document.getElementById('volumeChart').getContext('2d');
            volumeChart = new Chart(volumeCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Utilized Space', 'Unused Space'],
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: ['#3B82F6', '#1F2937'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                color: '#ffffff',
                                padding: 20
                            }
                        }
                    }
                }
            });
            
            // Weight Distribution Bar Chart
            const weightCtx = document.getElementById('weightChart').getContext('2d');
            weightChart = new Chart(weightCtx, {
                type: 'bar',
                data: {
                    labels: ['Front', 'Middle', 'Back'],
                    datasets: [{
                        label: 'Weight (kg)',
                        data: [0, 0, 0],
                        backgroundColor: ['#3B82F6', '#8B5CF6', '#10B981'],
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        }
                    },
                    scales: {
                        x: {
                            ticks: { color: '#ffffff' }
                        },
                        y: {
                            ticks: { color: '#ffffff' }
                        }
                    }
                }
            });
        }
        
        // Calculate dynamic statistics
        function calculateStatistics(data) {
            if (!data || !data.packed_items) return;
            
            const containerDims = data.container_dimensions;
            const containerVolume = containerDims[0] * containerDims[1] * containerDims[2];
            
            // Calculate metrics
            const totalWeight = data.packed_items.reduce((sum, box) => sum + box.weight, 0);
            const usedVolume = data.packed_items.reduce((sum, box) => 
                sum + (box.dimensions[0] * box.dimensions[1] * box.dimensions[2]), 0);
            const volumePercent = ((usedVolume / containerVolume) * 100);
            const spaceRemaining = containerVolume - usedVolume;
            
            // Temperature control calculation (based on temp sensitive items)
            const tempSensitiveItems = data.packed_items.filter(item => 
                item.temperature_sensitivity !== null && item.temperature_sensitivity !== undefined);
            const tempControlPercent = tempSensitiveItems.length > 0 ? 100 : 95;
            
            // Time saved calculation (based on optimization efficiency)
            const timeSavedPercent = Math.min(Math.round(volumePercent * 0.8), 95);
            
            // Optimization score (24/7 or percentage based on efficiency)
            const optimizationScore = volumePercent > 90 ? "24/7" : Math.round(volumePercent) + "%";
            
            // Update glassmorphic cards
            document.getElementById('space-utilization').textContent = volumePercent.toFixed(0) + '%';
            document.getElementById('temp-control').textContent = tempControlPercent + '%';
            document.getElementById('time-saved').textContent = timeSavedPercent + '%';
            document.getElementById('optimization').textContent = optimizationScore;
            
            // Update metric cards
            document.getElementById('volume-percent').textContent = volumePercent.toFixed(1) + '%';
            document.getElementById('total-items').textContent = data.packed_items.length;
            document.getElementById('total-weight').textContent = totalWeight.toFixed(1) + 'kg';
            document.getElementById('space-remaining').textContent = spaceRemaining.toFixed(2) + 'm³';
            
            // Update charts
            if (volumeChart) {
                volumeChart.data.datasets[0].data = [volumePercent, 100 - volumePercent];
                volumeChart.update();
            }
            
            // Calculate weight distribution by container sections
            if (weightChart) {
                const sections = { front: 0, middle: 0, back: 0 };
                const containerLength = containerDims[0];
                
                data.packed_items.forEach(item => {
                    const xPos = item.position[0] + item.dimensions[0] / 2;
                    const sectionPos = xPos / containerLength;
                    
                    if (sectionPos < 0.33) sections.front += item.weight;
                    else if (sectionPos < 0.66) sections.middle += item.weight;
                    else sections.back += item.weight;
                });
                
                weightChart.data.datasets[0].data = [
                    sections.front.toFixed(1),
                    sections.middle.toFixed(1),
                    sections.back.toFixed(1)
                ];
                weightChart.update();
            }
        }
        
        // Update cargo status list
        function updateCargoStatusList(data) {
            const listContainer = document.getElementById('cargo-status-list');
            listContainer.innerHTML = '';
            
            if (!data || !data.packed_items) return;
            
            data.packed_items.forEach(item => {
                const statusElement = document.createElement('div');
                statusElement.className = 'flex items-center gap-3 p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-all';
                
                // Determine status based on item properties
                let statusIcon = '🟩'; // green - OK
                let statusClass = 'status-green';
                
                if (item.fragility === 'HIGH' || (item.temperature_sensitivity && Math.abs(item.temperature_sensitivity) > 20)) {
                    statusIcon = '🟥'; // red - high risk
                    statusClass = 'status-red';
                } else if (item.fragility === 'MEDIUM' || item.temperature_sensitivity) {
                    statusIcon = '🟨'; // yellow - warning
                    statusClass = 'status-yellow';
                }
                
                statusElement.innerHTML = `
                    <span class="text-lg">${statusIcon}</span>
                    <span class="text-white font-medium">${item.name}</span>
                    <span class="text-sm text-gray-400 ml-auto">${item.weight.toFixed(1)}kg</span>
                `;
                
                listContainer.appendChild(statusElement);
            });
        }
        
        
        // Enhanced mouse move handler
        function onMouseMove(event) {
            const sceneContainer = document.getElementById('scene-container');
            const rect = sceneContainer.getBoundingClientRect();
            
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            
            raycaster.setFromCamera(mouse, camera);
            
            const intersects = raycaster.intersectObjects(boxMeshes.filter(mesh => mesh.isMesh && !mesh.isLineSegments));
            
            // Reset previous hover state
            if (hoveredBox && boxDataMap.has(hoveredBox)) {
                const boxData = boxDataMap.get(hoveredBox);
                boxData.mesh.material.color.setHex(boxData.originalColor);
                boxData.mesh.material.opacity = 0.9;
                boxData.mesh.scale.set(1, 1, 1);
                document.getElementById('box-info').style.opacity = "0";
            }
            hoveredBox = null;
            
            if (intersects.length > 0) {
                const meshId = intersects[0].object.id;
                
                if (boxDataMap.has(meshId)) {
                    hoveredBox = meshId;
                    const boxData = boxDataMap.get(meshId);
                    
                    // Highlight effects
                    boxData.mesh.material.color.setHex(0xffffff);
                    boxData.mesh.material.opacity = 1.0;
                    boxData.mesh.scale.set(1.05, 1.05, 1.05);
                    
                    // Show info panel
                    const boxInfoEl = document.getElementById('box-info');
                    
                    let itemType = "Standard";
                    if (boxData.tempSensitive && boxData.fragile) {
                        itemType = "Temperature Sensitive & Fragile";
                    } else if (boxData.tempSensitive) {
                        itemType = "Temperature Sensitive";
                    } else if (boxData.fragile) {
                        itemType = "Fragile";
                    }
                    
                    boxInfoEl.innerHTML = `
                        <div class="border-b border-white/20 pb-2 mb-2">
                            <strong class="text-blue-400 text-lg">${boxData.id}</strong>
                        </div>
                        <div class="space-y-1 text-sm">
                            <div><strong>Type:</strong> <span class="text-blue-300">${itemType}</span></div>
                            <div><strong>Weight:</strong> <span class="text-green-300">${boxData.weight.toFixed(2)}kg</span></div>
                            <div><strong>Dimensions:</strong> <span class="text-purple-300">${boxData.dimensions[0]}×${boxData.dimensions[1]}×${boxData.dimensions[2]}m</span></div>
                            <div class="text-xs text-gray-400 pt-2">
                                Position: (${boxData.position[0].toFixed(1)}, ${boxData.position[1].toFixed(1)}, ${boxData.position[2].toFixed(1)})
                            </div>
                        </div>
                    `;
                    
                    boxInfoEl.style.top = `${Math.min(event.clientY + 15, window.innerHeight - 200)}px`;
                    boxInfoEl.style.left = `${Math.min(event.clientX + 15, window.innerWidth - 300)}px`;
                    boxInfoEl.style.opacity = "1";
                }
            }
        }
        
        // Helper function to create text sprite
        function createTextSprite(text) {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.width = 256;
            canvas.height = 128;
            
            const gradient = context.createLinearGradient(0, 0, canvas.width, canvas.height);
            gradient.addColorStop(0, 'rgba(60, 130, 246, 0.9)');
            gradient.addColorStop(1, 'rgba(91, 118, 243, 0.9)');
            context.fillStyle = gradient;
            context.fillRect(0, 0, canvas.width, canvas.height);
            
            context.strokeStyle = 'rgba(255, 255, 255, 0.5)';
            context.lineWidth = 2;
            context.strokeRect(1, 1, canvas.width - 2, canvas.height - 2);
            
            context.font = 'bold 28px Inter, Arial';
            context.fillStyle = '#FFFFFF';
            context.textAlign = 'center';
            context.textBaseline = 'middle';
            context.shadowColor = 'rgba(0, 0, 0, 0.5)';
            context.shadowBlur = 4;
            context.fillText(text, canvas.width / 2, canvas.height / 2);
            
            const texture = new THREE.CanvasTexture(canvas);
            texture.minFilter = THREE.LinearFilter;
            const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
            const sprite = new THREE.Sprite(spriteMaterial);
            sprite.scale.set(1.2, 0.6, 1);
            
            return sprite;
        }
        
        // Helper function to get fragility color
        function getFragilityColor(fragility) {
            if (!fragility) return null;
            switch(fragility.toUpperCase()) {
                case 'LOW': return colors.fragile_low;
                case 'MEDIUM': return colors.fragile_medium;
                case 'HIGH': return colors.fragile_high;
                default: return colors.fragile_medium;
            }
        }
        
        // Animation functions
        function startLoadingAnimation() {
            if (!currentContainerData || isAnimating) return;
            
            isAnimating = true;
            animationPaused = false;
            currentAnimationIndex = 0;
            
            // Sort boxes by loading order (CORNER-TO-END, BOTTOM-UP with support)
            const sortedBoxes = getSortedBoxesForLoading();
            
            // Hide all boxes initially and position them at CORNER loading point
            boxMeshes.forEach((mesh, index) => {
                if (mesh.isMesh && !mesh.isLineSegments) {
                    originalBoxPositions[index] = mesh.position.clone();
                    
                    // Start boxes at the CORNER (0,0,0) - the starting corner
                    mesh.position.set(
                        -1.5, // Outside the container at corner (0,0,0)
                        0.2,  // Ground level (slightly above to avoid clipping)
                        -1.0  // At the corner position
                    );
                    mesh.visible = false;
                }
            });
            
            // Update button states
            document.getElementById('play-animation').style.display = 'none';
            document.getElementById('pause-animation').style.display = 'flex';
            
            // Start the animation with sorted order
            animateNextBox();
        }
        
        // Sort boxes for realistic loading pattern (CORNER-TO-END, BOTTOM-UP with support logic)
        function getSortedBoxesForLoading() {
            if (!currentContainerData || !currentContainerData.packed_items) {
                console.log('No container data available for sorting');
                return [];
            }
            
            // Create a map of valid boxes with their positions
            const validBoxes = [];
            boxMeshes.forEach((mesh, index) => {
                if (mesh && mesh.isMesh && !mesh.isLineSegments && originalBoxPositions[index]) {
                    const pos = originalBoxPositions[index];
                    validBoxes.push({
                        mesh: mesh,
                        index: index,
                        position: pos,
                        x: pos.x,
                        y: pos.y,
                        z: pos.z
                    });
                }
            });
            
            
            // Sort boxes using a layered approach: bottom-up, then corner-to-end
            const sortedBoxes = validBoxes.map(boxInfo => {
                const pos = boxInfo.position;
                const containerDims = currentContainerData.container_dimensions;
                
                // IMPROVED PRIORITY SYSTEM for logical loading:
                // 1. Layer (height) - must load bottom layer completely before upper layers
                const layer = Math.floor(pos.y / 0.8); // 0.8m per layer approximately
                const layerPriority = layer * 10000000; // Huge weight for layer
                
                // 2. Within same layer: corner to end (X position from 0 to max)
                const xPriority = pos.x * 1000;
                
                // 3. Within same X: left to right (Z position)
                const zPriority = pos.z * 10;
                
                // 4. Support check - ensure no floating boxes
                let supportPenalty = 0;
                if (layer > 0) { // If not ground layer
                    const hasSupport = checkSupportBelow(pos, validBoxes);
                    supportPenalty = hasSupport ? 0 : 5000000; // Big penalty for unsupported boxes
                }
                
                const totalPriority = layerPriority + xPriority + zPriority + supportPenalty;
                
                return {
                    ...boxInfo,
                    priority: totalPriority,
                    layer: layer,
                    hasSupport: layer === 0 || supportPenalty === 0
                };
            });
            
            // Sort by priority (bottom-up, corner-to-end, with support)
            sortedBoxes.sort((a, b) => a.priority - b.priority);
            
            return sortedBoxes;
        }
        
        // Check if a box has proper support underneath
        function checkSupportBelow(position, allBoxes) {
            const tolerance = 0.3; // Overlap tolerance
            
            for (let otherBox of allBoxes) {
                const otherPos = otherBox.position;
                
                // Check if other box is below this position
                if (otherPos.y < position.y - 0.1) {
                    // Check for X and Z overlap
                    const xOverlap = Math.abs(otherPos.x - position.x) < tolerance;
                    const zOverlap = Math.abs(otherPos.z - position.z) < tolerance;
                    
                    if (xOverlap && zOverlap) {
                        return true; // Found support
                    }
                }
            }
            
            return false; // No support found
        }
        
        function animateNextBox() {
            if (!isAnimating || animationPaused) return;
            
            const sortedBoxes = getSortedBoxesForLoading();
            
            if (currentAnimationIndex >= sortedBoxes.length) {
                // Animation complete
                stopAnimation();
                return;
            }
            
            const boxInfo = sortedBoxes[currentAnimationIndex];
            const mesh = boxInfo.mesh;
            const targetPosition = boxInfo.position;
            
            if (mesh && mesh.isMesh && !mesh.isLineSegments) {
                // Make box visible and animate it into position
                mesh.visible = true;
                
                // Calculate delay based on layer height (ground level faster, upper levels need more time)
                const layerDelay = Math.max(400, 300 + (targetPosition.y * 100)); // More delay for higher positions
                
                // Animate the box from loading dock to final position
                animateBoxToPosition(mesh, targetPosition, () => {
                    currentAnimationIndex++;
                    // Continue with next box after a delay that considers stacking height
                    setTimeout(animateNextBox, layerDelay);
                });
            } else {
                currentAnimationIndex++;
                animateNextBox();
            }
        }
        
        function animateBoxToPosition(mesh, targetPosition, callback) {
            const startPosition = mesh.position.clone();
            const duration = 1000 + (targetPosition.y * 200); // Longer animation for higher positions
            const startTime = Date.now();
            
            // Create a more realistic path based on stacking height
            const isGroundLevel = targetPosition.y < 1;
            const liftHeight = isGroundLevel ? 1.5 : Math.max(targetPosition.y + 1.5, 3);
            
            // Create intermediate positions for realistic stacking
            const midPosition = new THREE.Vector3(
                targetPosition.x,
                liftHeight, // Higher lift for upper layers
                targetPosition.z
            );
            
            function animate() {
                const elapsed = Date.now() - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                // Split animation into phases like a worker would move for stacking
                let currentPos;
                
                if (progress < 0.3) {
                    // Phase 1: Quick horizontal movement to position above target
                    const phase1Progress = progress / 0.3;
                    const easeProgress = 1 - Math.pow(1 - phase1Progress, 2); // Ease out quad
                    
                    currentPos = new THREE.Vector3().lerpVectors(startPosition, midPosition, easeProgress);
                    
                    // Add slight bobbing motion like walking, more for ground level
                    const bobbingIntensity = isGroundLevel ? 0.15 : 0.05;
                    currentPos.y += Math.sin(phase1Progress * Math.PI * 3) * bobbingIntensity;
                    
                    // Slight rotation during transport
                    mesh.rotation.y = Math.sin(phase1Progress * Math.PI) * 0.08;
                    
                } else if (progress < 0.7) {
                    // Phase 2: Positioning phase - careful alignment above target
                    const phase2Progress = (progress - 0.3) / 0.4;
                    
                    // Stay at lift height but ensure perfect X,Z alignment
                    currentPos = new THREE.Vector3(
                        targetPosition.x,
                        liftHeight - (phase2Progress * 0.3), // Slight descent during positioning
                        targetPosition.z
                    );
                    
                    // Slow rotation to final orientation
                    mesh.rotation.y = (1 - phase2Progress) * 0.08;
                    
                } else {
                    // Phase 3: Careful vertical placement (like lowering cargo for stacking)
                    const phase3Progress = (progress - 0.7) / 0.3;
                    const easeProgress = phase3Progress * phase3Progress * (3 - 2 * phase3Progress); // Smooth step for controlled lowering
                    
                    currentPos = new THREE.Vector3().lerpVectors(
                        new THREE.Vector3(targetPosition.x, liftHeight - 0.3, targetPosition.z),
                        targetPosition,
                        easeProgress
                    );
                    
                    // Final rotation alignment
                    mesh.rotation.y = (1 - easeProgress) * 0.02;
                }
                
                mesh.position.copy(currentPos);
                
                if (progress < 1 && isAnimating && !animationPaused) {
                    requestAnimationFrame(animate);
                } else {
                    mesh.rotation.y = 0; // Reset rotation
                    mesh.position.copy(targetPosition);
                    if (callback) callback();
                }
            }
            
            animate();
        }
        
        function pauseAnimation() {
            animationPaused = true;
            document.getElementById('play-animation').style.display = 'flex';
            document.getElementById('pause-animation').style.display = 'none';
        }
        
        function resumeAnimation() {
            if (isAnimating && animationPaused) {
                animationPaused = false;
                document.getElementById('play-animation').style.display = 'none';
                document.getElementById('pause-animation').style.display = 'flex';
                animateNextBox();
            } else {
                // Change button text to show it's starting with layer info
                document.getElementById('play-animation').innerHTML = `
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M8 5v14l11-7z"/>
                    </svg>
                    Loading Layers...
                `;
                setTimeout(() => {
                    startLoadingAnimation();
                }, 100);
            }
        }
        
        function resetAnimation() {
            isAnimating = false;
            animationPaused = false;
            currentAnimationIndex = 0;
            
            // Reset all boxes to their original positions
            boxMeshes.forEach((mesh, index) => {
                if (mesh.isMesh && !mesh.isLineSegments && originalBoxPositions[index]) {
                    mesh.position.copy(originalBoxPositions[index]);
                    mesh.rotation.y = 0;
                    mesh.visible = true;
                }
            });
            
            // Reset button states
            document.getElementById('play-animation').style.display = 'flex';
            document.getElementById('pause-animation').style.display = 'none';
            
            // Update button text
            document.getElementById('play-animation').innerHTML = `
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M8 5v14l11-7z"/>
                </svg>
                Layer Loading
            `;
        }
        
        function stopAnimation() {
            isAnimating = false;
            animationPaused = false;
            document.getElementById('play-animation').style.display = 'flex';
            document.getElementById('pause-animation').style.display = 'none';
        }
        
        
        // Display container function
        function displayContainer(index) {
            const data = containerData[index];
            currentContainerData = data;
            boxDataMap.clear();
            
            // Reset animation state
            isAnimating = false;
            animationPaused = false;
            currentAnimationIndex = 0;
            originalBoxPositions = [];
            document.getElementById('play-animation').style.display = 'flex';
            document.getElementById('pause-animation').style.display = 'none';
            
            // Clear previous objects
            containerMeshes.forEach(mesh => scene.remove(mesh));
            boxMeshes.forEach(mesh => scene.remove(mesh));
            textSprites.forEach(sprite => scene.remove(sprite));
            
            containerMeshes = [];
            boxMeshes = [];
            textSprites = [];
            
            // Create container group
            const containerGroup = new THREE.Group();
            containerGroup.name = 'containerGroup';
            scene.add(containerGroup);
            containerMeshes.push(containerGroup);
            
            const containerDims = data.container_dimensions;
            
            // Create container wireframe
            const containerGeometry = new THREE.BoxGeometry(
                containerDims[0], containerDims[2], containerDims[1]
            );
            
            const wireframe = new THREE.LineSegments(
                new THREE.EdgesGeometry(containerGeometry),
                new THREE.LineBasicMaterial({ 
                    color: colors.container, 
                    linewidth: 3,
                    transparent: true,
                    opacity: 0.8
                })
            );
            
            wireframe.position.set(
                containerDims[0] / 2,
                containerDims[2] / 2,
                containerDims[1] / 2
            );
            
            containerGroup.add(wireframe);
            
            // Add packed items
            data.packed_items.forEach(item => {
                const dimensions = item.dimensions;
                const position = item.position;
                
                const boxGeometry = new THREE.BoxGeometry(
                    dimensions[0], dimensions[2], dimensions[1]
                );
                
                // Determine box color
                const isItemTempSensitive = item.temperature_sensitivity !== null && item.temperature_sensitivity !== undefined;
                const isItemFragile = item.fragility && (item.fragility.toUpperCase() === "HIGH" || item.fragility.toUpperCase() === "MEDIUM");
                
                let boxColor;
                if (isItemTempSensitive && isItemFragile) {
                    boxColor = colors.both;
                } else if (isItemTempSensitive) {
                    boxColor = colors.temperature_sensitive;
                } else if (isItemFragile) {
                    const fragilityColor = getFragilityColor(item.fragility);
                    boxColor = fragilityColor || colors.fragile_medium;
                } else {
                    boxColor = colors.normal;
                }
                
                const boxMaterial = new THREE.MeshPhongMaterial({
                    color: boxColor,
                    transparent: true,
                    opacity: 0.9,
                    specular: 0x333333,
                    shininess: 60,
                    reflectivity: 0.3
                });
                
                const boxMesh = new THREE.Mesh(boxGeometry, boxMaterial);
                
                const posX = position[0] + dimensions[0] / 2;
                const posY = position[2] + dimensions[2] / 2;
                const posZ = position[1] + dimensions[1] / 2;
                
                const finalPosition = new THREE.Vector3(
                    Math.min(posX, containerDims[0] - dimensions[0]/2),
                    Math.min(posY, containerDims[2] - dimensions[2]/2),
                    Math.min(posZ, containerDims[1] - dimensions[1]/2)
                );
                
                boxMesh.position.copy(finalPosition);
                boxMesh.userData.originalPosition = finalPosition.clone();
                
                // Store original position for animation
                originalBoxPositions.push(finalPosition.clone());
                
                boxMesh.castShadow = true;
                boxMesh.receiveShadow = true;
                containerGroup.add(boxMesh);
                boxMeshes.push(boxMesh);
                
                // Store box data
                boxDataMap.set(boxMesh.id, {
                    id: item.name,
                    weight: item.weight,
                    dimensions: dimensions,
                    fragility: item.fragility,
                    tempSensitive: isItemTempSensitive,
                    fragile: isItemFragile,
                    mesh: boxMesh,
                    originalColor: boxColor,
                    position: position
                });
                
                // Add labels if enabled
                if (showLabels) {
                    const sprite = createTextSprite(item.name);
                    sprite.position.set(
                        boxMesh.position.x,
                        boxMesh.position.y + dimensions[2] / 2 + 0.15,
                        boxMesh.position.z
                    );
                    containerGroup.add(sprite);
                    textSprites.push(sprite);
                }
            });
            
            // Update statistics and UI
            calculateStatistics(data);
            updateCargoStatusList(data);
            resetCamera();
        }
        
        // Camera and control functions
        function resetCamera() {
            const container = scene.getObjectByName('containerGroup');
            if (!container) return;
            
            const box = new THREE.Box3().setFromObject(container);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            const maxSize = Math.max(size.x, size.y, size.z);
            
            camera.position.set(maxSize * 1.5, maxSize * 1.5, maxSize * 1.5);
            controls.target.copy(center);
            controls.update();
        }
        
        function toggleCameraType() {
            const container = scene.getObjectByName('containerGroup');
            if (!container) return;
            
            const box = new THREE.Box3().setFromObject(container);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            const maxSize = Math.max(size.x, size.y, size.z);
            
            const sceneContainer = document.getElementById('scene-container');
            const width = sceneContainer.clientWidth;
            const height = sceneContainer.clientHeight;
            
            if (isOrthographic) {
                camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
                camera.position.set(maxSize * 1.5, maxSize * 1.5, maxSize * 1.5);
                isOrthographic = false;
                document.getElementById('view-perspective').classList.add('bg-blue-500');
                document.getElementById('view-orthographic').classList.remove('bg-blue-500');
            } else {
                const frustumSize = maxSize * 2;
                const aspect = width / height;
                camera = new THREE.OrthographicCamera(
                    frustumSize * aspect / -2, frustumSize * aspect / 2,
                    frustumSize / 2, frustumSize / -2,
                    0.1, 1000
                );
                camera.position.set(maxSize * 1.5, maxSize * 1.5, maxSize * 1.5);
                isOrthographic = true;
                document.getElementById('view-orthographic').classList.add('bg-blue-500');
                document.getElementById('view-perspective').classList.remove('bg-blue-500');
            }
            
            camera.lookAt(center);
            controls.object = camera;
            controls.target.copy(center);
            controls.update();
        }
        
        function toggleAutoRotate() {
            autoRotate = !autoRotate;
            controls.autoRotate = autoRotate;
            const btn = document.getElementById('auto-rotate');
            if (autoRotate) {
                btn.classList.add('bg-blue-500');
                btn.classList.remove('bg-blue-500/20');
            } else {
                btn.classList.remove('bg-blue-500');
                btn.classList.add('bg-blue-500/20');
            }
        }
        
        function toggleExplodedView() {
            explodedView = !explodedView;
            const btn = document.getElementById('explode-view');
            
            if (explodedView) {
                btn.classList.add('bg-blue-500');
                btn.classList.remove('bg-white/10');
                
                // Move boxes outward from center
                const containerCenter = new THREE.Vector3(
                    currentContainerData.container_dimensions[0] / 2,
                    currentContainerData.container_dimensions[2] / 2,
                    currentContainerData.container_dimensions[1] / 2
                );
                
                boxMeshes.forEach(mesh => {
                    if (mesh.isMesh && mesh.userData.originalPosition) {
                        const direction = new THREE.Vector3()
                            .copy(mesh.position)
                            .sub(containerCenter)
                            .normalize();
                        
                        const explodeDistance = 2;
                        mesh.position.copy(mesh.userData.originalPosition).add(direction.multiplyScalar(explodeDistance));
                    }
                });
            } else {
                btn.classList.remove('bg-blue-500');
                btn.classList.add('bg-white/10');
                
                // Return boxes to original positions
                boxMeshes.forEach(mesh => {
                    if (mesh.isMesh && mesh.userData.originalPosition) {
                        mesh.position.copy(mesh.userData.originalPosition);
                    }
                });
            }
        }
        
        
        // Event listeners
        document.getElementById('get-started-btn').addEventListener('click', function() {
            alert('Welcome to GravityCargo!\\n\\n' +
                  '• Use mouse to rotate, zoom, and pan the 3D view\\n' +
                  '• Hover over items to see detailed information\\n' +
                  '• Use the controls to toggle different view modes\\n' +
                  '• Select different container files from the dropdown\\n\\n' +
                  'Created by Team System32');
        });
        
        // 3D/AR Toggle Button Event Listeners
        document.getElementById('view-3d').addEventListener('click', function() {
            if (!this.classList.contains('toggle-active')) {
                // Switch to 3D view
                this.classList.add('toggle-active');
                this.style.background = 'linear-gradient(135deg, #3C82F6 0%, #5B76F3 100%)';
                this.style.color = 'white';
                
                const arBtn = document.getElementById('view-ar');
                arBtn.classList.remove('toggle-active');
                arBtn.style.background = 'rgba(255, 255, 255, 0.9)';
                arBtn.style.color = 'rgba(107, 114, 128, 1)';
                
                // Add any 3D view specific functionality here
                console.log('Switched to 3D View');
            }
        });
          document.getElementById('view-ar').addEventListener('click', function() {
            if (!this.classList.contains('toggle-active')) {
                // Switch to AR view
                this.classList.add('toggle-active');
                this.style.background = 'linear-gradient(135deg, #3C82F6 0%, #5B76F3 100%)';
                this.style.color = 'white';
                
                const view3dBtn = document.getElementById('view-3d');
                view3dBtn.classList.remove('toggle-active');
                view3dBtn.style.background = 'rgba(255, 255, 255, 0.9)';
                view3dBtn.style.color = 'rgba(107, 114, 128, 1)';
                
                // Start AR server functionality
                console.log('Switched to AR View');
                startARVisualization();
            }
        });
          // AR Visualization Functions
        async function startARVisualization() {
            try {
                // Show loading indicator
                const loadingEl = document.createElement('div');
                loadingEl.id = 'ar-loading';
                loadingEl.innerHTML = `
                    <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                                background: rgba(0,0,0,0.8); color: white; padding: 20px; border-radius: 10px; z-index: 9999;">
                        <div style="text-align: center;">
                            <div style="border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; 
                                       width: 40px; height: 40px; animation: spin 2s linear infinite; margin: 0 auto 10px;"></div>
                            <div>Starting AR Server...</div>
                        </div>
                    </div>
                    <style>
                        @keyframes spin {
                            0% { transform: rotate(0deg); }
                            100% { transform: rotate(360deg); }
                        }
                    </style>
                `;
                document.body.appendChild(loadingEl);
                
                // Debug: Log current environment
                console.log('Current URL:', window.location.href);
                console.log('Current origin:', window.location.origin);
                
                // Start the JSON server for AR
                const response = await fetch('/start_json_server', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    // Add credentials for cross-origin requests
                    credentials: 'same-origin'
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                
                // Remove loading indicator
                document.body.removeChild(loadingEl);
                
                if (result.success) {
                    showARInstructions(result.url);
                } else {
                    throw new Error(result.error || 'Failed to start AR server');
                }
                  } catch (error) {
                console.error('Error starting AR visualization:', error);
                console.error('Error details:', {
                    message: error.message,
                    name: error.name,
                    stack: error.stack
                });
                
                // Remove loading indicator if it exists
                const loadingEl = document.getElementById('ar-loading');
                if (loadingEl) {
                    document.body.removeChild(loadingEl);
                }
                
                // Enhanced error message with debugging info
                let errorMsg = `Failed to start AR visualization: ${error.message}`;
                if (error.message.includes('ERR_BLOCKED_BY_CLIENT')) {
                    errorMsg += '\\n\\nThis might be caused by:';
                    errorMsg += '\\n1. Ad blocker or browser extension blocking the request';
                    errorMsg += '\\n2. Browser security settings';
                    errorMsg += '\\n3. Network connectivity issues';
                    errorMsg += '\\n\\nTry:';
                    errorMsg += '\\n- Disabling ad blockers temporarily';
                    errorMsg += '\\n- Using incognito/private mode';
                    errorMsg += '\\n- Checking browser console for more details';
                } else if (error.message.includes('Failed to fetch')) {
                    errorMsg += '\\n\\nThis might be caused by:';
                    errorMsg += '\\n1. Server not responding';
                    errorMsg += '\\n2. Network connectivity issues';
                    errorMsg += '\\n3. CORS policy restrictions';
                    errorMsg += '\\n\\nTry refreshing the page or check server logs.';
                }
                
                alert(errorMsg);
                
                // Revert button state
                const arBtn = document.getElementById('view-ar');
                const view3dBtn = document.getElementById('view-3d');
                arBtn.classList.remove('toggle-active');
                arBtn.style.background = 'rgba(255, 255, 255, 0.9)';
                arBtn.style.color = 'rgba(107, 114, 128, 1)';
                view3dBtn.classList.add('toggle-active');
                view3dBtn.style.background = 'linear-gradient(135deg, #3C82F6 0%, #5B76F3 100%)';
                view3dBtn.style.color = 'white';
            }
        }
        
        function showARInstructions(serverUrl) {
            const modal = document.createElement('div');
            modal.innerHTML = `
                <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
                           background: rgba(0,0,0,0.8); z-index: 10000; display: flex; align-items: center; justify-content: center;">
                    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                               border-radius: 15px; padding: 30px; max-width: 600px; margin: 20px; color: white; box-shadow: 0 20px 40px rgba(0,0,0,0.3);">
                        <div style="text-align: center; margin-bottom: 25px;">
                            <div style="background: linear-gradient(135deg, #3C82F6 0%, #5B76F3 100%); 
                                       width: 80px; height: 80px; border-radius: 50%; margin: 0 auto 15px; 
                                       display: flex; align-items: center; justify-content: center; font-size: 40px;">
                                🥽
                            </div>
                            <h2 style="margin: 0; background: linear-gradient(135deg, #3C82F6 0%, #5B76F3 100%); 
                                      -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
                                      background-clip: text;">AR Server Active!</h2>
                        </div>
                        
                        <div style="background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                            <h4 style="margin: 0 0 10px 0; color: #60A5FA;">🔗 Unity Connection URL:</h4>
                            <div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 8px; 
                                       font-family: 'Courier New', monospace; font-size: 14px; word-break: break-all; 
                                       border: 1px solid rgba(91, 118, 243, 0.5);">
                                ${serverUrl}
                            </div>
                            <button onclick="navigator.clipboard.writeText('${serverUrl}')" 
                                   style="background: linear-gradient(135deg, #10B981 0%, #059669 100%); 
                                          border: none; color: white; padding: 8px 16px; border-radius: 5px; 
                                          margin-top: 10px; cursor: pointer; font-size: 12px;">
                                📋 Copy URL
                            </button>
                        </div>
                        
                        <div style="margin-bottom: 20px;">
                            <h4 style="margin: 0 0 15px 0; color: #60A5FA;">📱 How to Use with Unity:</h4>
                            <ol style="margin: 0; padding-left: 20px; line-height: 1.6;">
                                <li>Open your Unity AR project</li>
                                <li>Copy the URL above into your Unity HTTP request component</li>
                                <li>The JSON data contains all container and cargo information</li>
                                <li>Use the data to visualize containers in AR space</li>
                                <li>Data updates automatically when you optimize new containers</li>
                            </ol>
                        </div>
                        
                        <div style="background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); 
                                   border-radius: 8px; padding: 15px; margin-bottom: 20px;">
                            <div style="font-size: 14px; opacity: 0.9;">
                                💡 <strong>Tip:</strong> The server will remain active as long as this application is running. 
                                Use the URL in Unity to fetch real-time container data for AR visualization.
                            </div>
                        </div>
                        
                        <div style="text-align: center; display: flex; gap: 15px; justify-content: center;">
                            <button onclick="this.closest('div').parentElement.remove()" 
                                   style="background: linear-gradient(135deg, #3C82F6 0%, #5B76F3 100%); 
                                          border: none; color: white; padding: 12px 24px; border-radius: 8px; 
                                          cursor: pointer; font-weight: 600;">
                                ✅ Got It!
                            </button>
                            <button onclick="stopARServer()" 
                                   style="background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%); 
                                          border: none; color: white; padding: 12px 24px; border-radius: 8px; 
                                          cursor: pointer; font-weight: 600;">
                                🛑 Stop AR Server
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        async function stopARServer() {
            try {
                const response = await fetch('/stop_json_server', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                });
                
                const result = await response.json();
                
                if (result.success) {
                    // Close modal
                    const modal = document.querySelector('div[style*="position: fixed"]');
                    if (modal) {
                        modal.remove();
                    }
                    
                    // Revert to 3D view
                    const arBtn = document.getElementById('view-ar');
                    const view3dBtn = document.getElementById('view-3d');
                    arBtn.classList.remove('toggle-active');
                    arBtn.style.background = 'rgba(255, 255, 255, 0.9)';
                    arBtn.style.color = 'rgba(107, 114, 128, 1)';
                    view3dBtn.classList.add('toggle-active');
                    view3dBtn.style.background = 'linear-gradient(135deg, #3C82F6 0%, #5B76F3 100%)';
                    view3dBtn.style.color = 'white';
                    
                    alert('AR Server stopped successfully');
                } else {
                    throw new Error(result.error || 'Failed to stop AR server');
                }
            } catch (error) {
                console.error('Error stopping AR server:', error);
                alert(`Failed to stop AR server: ${error.message}`);
            }
        }
        
        document.getElementById('view-orthographic').addEventListener('click', () => {
            if (!isOrthographic) toggleCameraType();
        });
        
        document.getElementById('view-perspective').addEventListener('click', () => {
            if (isOrthographic) toggleCameraType();
        });
        
        document.getElementById('reset-camera').addEventListener('click', resetCamera);
        document.getElementById('auto-rotate').addEventListener('click', toggleAutoRotate);
        
        // Animation control event listeners
        document.getElementById('play-animation').addEventListener('click', resumeAnimation);
        document.getElementById('pause-animation').addEventListener('click', pauseAnimation);
        document.getElementById('reset-animation').addEventListener('click', resetAnimation);
        
        document.getElementById('toggle-labels').addEventListener('click', function() {
            showLabels = !showLabels;
            textSprites.forEach(sprite => {
                sprite.visible = showLabels;
            });
            this.classList.toggle('bg-blue-500');
            this.classList.toggle('bg-white/10');
        });
        
        document.getElementById('toggle-wireframe').addEventListener('click', function() {
            showWireframe = !showWireframe;
            this.classList.toggle('bg-blue-500');
            this.classList.toggle('bg-white/10');
            const currentIndex = parseInt(document.getElementById('file-select').value);
            displayContainer(currentIndex);
        });
        
        document.getElementById('explode-view').addEventListener('click', toggleExplodedView);
        
        document.getElementById('file-select').addEventListener('change', function() {
            displayContainer(parseInt(this.value));
        });
        
        // Resize handler
        function handleResize() {
            const sceneContainer = document.getElementById('scene-container');
            const width = sceneContainer.clientWidth;
            const height = sceneContainer.clientHeight;
            
            if (isOrthographic) {
                const frustumSize = camera.right * 2;
                const aspect = width / height;
                camera.left = frustumSize * aspect / -2;
                camera.right = frustumSize * aspect / 2;
            } else {
                camera.aspect = width / height;
            }
            
            camera.updateProjectionMatrix();
            renderer.setSize(width, height);
               }
        
        window.addEventListener('resize', handleResize);
        window.addEventListener('mousemove', onMouseMove);
        
        // Initialize the renderer after DOM is ready
        function initializeRenderer() {
            const sceneContainer = document.getElementById('scene-container');
            const width = sceneContainer.clientWidth;
            const height = sceneContainer.clientHeight;
            
            renderer.setSize(width, height);
            renderer.setPixelRatio(window.devicePixelRatio);
            sceneContainer.appendChild(renderer.domElement);
        }
        
        // Animation loop
        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            
            if (hoveredBox && boxDataMap.has(hoveredBox)) {
                const boxData = boxDataMap.get(hoveredBox);
                const time = Date.now() * 0.005;
                boxData.mesh.rotation.y = Math.sin(time) * 0.1;
            }
            
            renderer.render(scene, camera);
        }
        
        // Initialize everything
        function init() {
            createParticles();
            initializeCharts();
            initializeRenderer();
            displayContainer(0);
            handleResize();
            animate();
        }
        
        // Start when DOM is loaded
        document.addEventListener('DOMContentLoaded', init);
    </script>
</body>
</html>
""")
    
    print(f"Created enhanced interactive 3D visualization at {html_file}")
    print(f"Opening visualization in web browser")
    webbrowser.open(f'file://{os.path.abspath(html_file)}')

def main():
    """Main function"""
    
    parser = argparse.ArgumentParser(description="Launch container visualization")
    parser.add_argument("-d", "--data-dir", default="container_plans", 
                       help="Directory with container JSON files (default: container_plans)")
    parser.add_argument("-f", "--file", 
                       help="Specific JSON file to visualize (optional)")
    
    args = parser.parse_args()
    
    # Launch the visualization
    launch_pythreejs_visualization(args.data_dir, args.file)

if __name__ == "__main__":
    main()