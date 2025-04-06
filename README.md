# GravitycARgo - Advanced Container Optimization System

![GravitycARgo Logo](static/images/logo.png)

## Live Demo

[https://gravitycargo-deploy.onrender.com/](https://gravitycargo-deploy.onrender.com/)

## Project Overview

GravitycARgo is an advanced container packing optimization system that uses genetic algorithms enhanced with LLM-powered adaptive mutation strategies to solve complex 3D bin packing problems efficiently. This application helps logistics companies, warehouses, and shipping operations maximize container space utilization, reduce shipping costs, and streamline operations.

The system employs a sophisticated approach to container loading optimization:

- **Genetic Algorithm Optimization**: Evolves packing solutions through generations
- **LLM-Powered Adaptive Mutations**: Dynamically adjusts mutation strategies based on optimization progress
- **3D Visualization**: Provides an interactive visualization of container loading plans
- **Real-time Optimization**: Displays the optimization process as it happens
- **Multi-Objective Optimization**: Balances volume utilization, stability, and load balancing

## Key Features

- **Interactive Web Interface**: User-friendly dashboard for uploading inventory data and managing optimizations
- **Multiple Container Types**: Support for various standard shipping container sizes
- **Real-time Optimization Tracking**: Monitor the optimization process as it evolves
- **3D Visualization**: Interactive visualization of packed containers
- **Downloadable Reports**: Export packing plans in various formats (JSON, CSV, PDF)
- **Alternative Solutions**: Generate and compare multiple packing solutions
- **Multi-Objective Optimization**: Combines volume utilization, stability, and load balancing

## Technology Stack

- **Backend**: Python, Flask, Flask-SocketIO
- **Frontend**: HTML5, CSS3, JavaScript, Three.js (for 3D visualization)
- **Optimization Engine**: Custom genetic algorithm implementation with LLM adaptation
- **Data Processing**: Pandas, NumPy
- **Visualization**: Plotly, Dash
- **Deployment**: Render

## Installation

### Prerequisites

- Python 3.11 or newer
- pip package manager
- Git (optional, for cloning the repository)

### Setup

1. Clone the repository (or download and extract the ZIP file):

```bash
git clone https://github.com/System32-official/GravitycARgo---deploy.git
cd GravitycARgo---deploy
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables (create a `.env` file):

```
SECRET_KEY=your_secret_key
GROQ_API_KEY=your_groq_api_key   # Optional: For LLM-powered features
GEMINI_API_KEY=your_gemini_api_key  # Optional: Alternative LLM provider
```

## Running the Application

### Local Development

1. Start the development server:

```bash
python app.py
```

2. Open your web browser and navigate to:

```
http://localhost:5000
```

### Production Deployment

For production deployment, use Gunicorn with the configured parameters:

```bash
gunicorn --worker-class geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 --timeout 300 wsgi:app
```

## Usage Guide

### Basic Workflow

1. **Start**: Navigate to the home page and click "Start"
2. **Upload Data**: Upload a CSV file containing your inventory items (see format below)
3. **Select Container**: Choose a container type and transport mode
4. **Optimize**: Start the optimization process
5. **View Results**: Explore the 3D visualization of the packed container
6. **Download Reports**: Export the packing plan

### CSV Format

Your inventory data CSV should follow this format:

```
item_name,length,width,height,weight,quantity
Box A,60,40,30,15,5
Box B,30,25,20,8,10
```

Units should be in centimeters for dimensions and kilograms for weight.

## Optimization Engine

The core of GravitycARgo is its advanced genetic algorithm optimization engine:

- **Population Size**: 20 solutions by default
- **Generations**: 30 by default
- **Fitness Function**: Multi-objective function considering:
  - Volume utilization (35%)
  - Wall contact points (35%)
  - Stability (15%)
  - Load balance (10%)
  - Packing ratio (5%)
- **LLM-Powered Adaptation**: Dynamically adjusts mutation strategies based on optimization progress

## Project Structure

- `app.py` & `app_modular.py`: Main application entry points
- `wsgi.py`: WSGI entry point for production servers
- `optigenix_module/`: Core optimization engine components
  - `optimization/`: Genetic algorithm implementation
  - `models/`: Container and item models
  - `utils/`: Utility functions and LLM connector
- `modules/`: Web application modules
- `static/`: Frontend assets
- `templates/`: HTML templates
- `uploads/`: Directory for uploaded inventory files
- `container_plans/`: Saved container packing plans

## Contributing

Contributions to GravitycARgo are welcome! Please feel free to submit issues, feature requests, or pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Three.js library for 3D visualization
- Plotly and Dash for data visualization
- Google Gemini & Groq for LLM capabilities

---

Developed with ❤️ by System32-official
