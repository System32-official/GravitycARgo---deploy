"""
Route handler functions for the container packing application
"""
from flask import request, redirect, url_for, render_template, send_file, jsonify, session, Blueprint, current_app
from werkzeug.utils import secure_filename
import pandas as pd
from io import BytesIO

# Import from config instead of app_modular
from config import PLANS_FOLDER, ALLOWED_EXTENSIONS

import json
import datetime
import os
import numpy as np
import random  # Required for item color generation

# Import directly from the new optigenix_module structure
from optigenix_module.constants import CONTAINER_TYPES, TRANSPORT_MODES
from optigenix_module.models.item import Item
from optigenix_module.models.container import EnhancedContainer
from optigenix_module.models.space import MaximalSpace

from modules.models import ContainerStorage
from modules.visualization import create_interactive_visualization, add_unpacked_table
from modules.report import generate_detailed_report
from modules.utils import allowed_file, cleanup_old_files
from modules.stability import analyze_layer_distribution, analyze_stability

# Create a blueprint
bp = Blueprint('handlers', __name__)

# Create container storage
container_storage = ContainerStorage()

def landing_handler():
    """Handle the landing page route"""
    return render_template('landing.html')

def start_handler():
    """Handle the start page route"""
    # Format transport modes and their supported containers
    formatted_modes = []
    for mode_id, (mode_name, containers) in TRANSPORT_MODES.items():
        container_details = []
        for container_name in containers:
            if container_name in CONTAINER_TYPES:
                dims = CONTAINER_TYPES[container_name]
                container_details.append({
                    'name': container_name,
                    'dimensions': dims,
                    'volume': dims[0] * dims[1] * dims[2]
                })
        
        formatted_modes.append({
            'id': mode_id,
            'name': mode_name,
            'containers': container_details
        })

    # Add default data for JavaScript
    default_data = {
        'transport_modes': formatted_modes,
        'container_types': CONTAINER_TYPES
    }

    return render_template('index.html', data=default_data)

def optimize_handler():
    """Handle the optimize route"""
    try:
        # Enable debug logging
        current_app.logger.info("Optimize route called")
        
        cleanup_old_files()  # Cleanup old uploads
        
        # Validate file
        if 'file' not in request.files:
            current_app.logger.error("No file in request")
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if file.filename == '':
            current_app.logger.error("Empty filename")
            return jsonify({'error': 'No file selected'}), 400
            
        if not allowed_file(file.filename):
            current_app.logger.error(f"Invalid file type: {file.filename}")
            return jsonify({'error': 'Invalid file type. Please upload a CSV or Excel file'}), 400

        # Validate transport mode and container selection
        transport_mode = request.form.get('transport_mode')
        container_type = request.form.get('container_type')
        
        current_app.logger.info(f"Transport mode: {transport_mode}, Container type: {container_type}")
        
        # Create container_info dictionary
        container_info = {
            'type': container_type if transport_mode != '5' else 'Custom',
            'transport_mode': TRANSPORT_MODES[transport_mode][0]  # Gets mode name like 'Sea Transport'
        }
        
        # Get container dimensions
        try:
            if transport_mode == '5':
                dimensions = (
                    float(request.form['length']),
                    float(request.form['width']),
                    float(request.form['height'])
                )
                container_info['dimensions'] = f"{dimensions[0]}m × {dimensions[1]}m × {dimensions[2]}m"
            else:
                # Get the first three elements from CONTAINER_TYPES (length, width, height)
                container_dims = CONTAINER_TYPES[container_type]
                dimensions = (float(container_dims[0]), float(container_dims[1]), float(container_dims[2]))
                container_info['dimensions'] = f"{dimensions[0]}m × {dimensions[1]}m × {dimensions[2]}m"
                
            # Log the dimensions to help debug
            current_app.logger.info(f"Container dimensions: {dimensions}, type: {type(dimensions)}, length: {len(dimensions)}")
                
        except (ValueError, KeyError) as e:
            current_app.logger.error(f"Error with container dimensions: {str(e)}")
            return jsonify({'error': f'Invalid container dimensions: {str(e)}'}), 400

        # Save and process file
        filename = secure_filename(file.filename)
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        current_app.logger.info(f"File saved at: {filepath}")
        
        # Create container and load items
        container = EnhancedContainer(dimensions)
        
        # Determine file type and read accordingly
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        if file_ext == 'csv':
            df = pd.read_csv(filepath)
        elif file_ext in ['xlsx', 'xls']:
            df = pd.read_excel(filepath)
        else:
            return jsonify({'error': 'Unsupported file format'}), 400
        
        current_app.logger.info(f"File loaded with {len(df)} rows")
        current_app.logger.debug(f"File columns: {df.columns.tolist()}")
        
        # Validate and standardize column names
        required_columns = ['Name', 'Length', 'Width', 'Height', 'Weight', 'Quantity', 'Fragility', 'BoxingType', 'Bundle']
        column_mapping = {
            'stackable': ['Stackable', 'LoadBearing', 'CanStack', 'Stack'],
            'fragility': ['Fragility', 'Fragile', 'FragilityLevel'],
            'boxing_type': ['BoxingType', 'PackagingType', 'Package'],
            'bundle': ['Bundle', 'IsBundled', 'Bundled'],
            'temperature_sensitivity': ['Temperature Sensitivity', 'TemperatureSensitivity', 'TempSensitivity']
        }
        
        # Check required columns
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            current_app.logger.error(f"Missing columns: {missing_columns}")
            return jsonify({'error': f'Missing required columns: {", ".join(missing_columns)}'}), 400
            
        # Find stackable column
        stackable_col = None
        for possible_name in column_mapping['stackable']:
            if possible_name in df.columns:
                stackable_col = possible_name
                break
        
        # Find temperature sensitivity column
        temp_sensitivity_col = None
        for possible_name in column_mapping['temperature_sensitivity']:
            if possible_name in df.columns:
                temp_sensitivity_col = possible_name
                break
        
        current_app.logger.info(f"Using stackable column: {stackable_col}, temperature sensitivity column: {temp_sensitivity_col}")
        
        # Get route temperature from form if provided
        route_temperature = None
        if 'route_temperature' in request.form and request.form['route_temperature']:
            try:
                route_temperature = float(request.form['route_temperature'])
                current_app.logger.info(f"Using route temperature: {route_temperature}°C")
                container_info['route_temperature'] = route_temperature
            except ValueError:
                current_app.logger.warning(f"Invalid route temperature: {request.form['route_temperature']}")
        
        items = []
        warnings = []
        
        for _, row in df.iterrows():
            try:
                # Get stackable value with default
                stackable_value = 'YES' if stackable_col and row[stackable_col] in ['YES', 'Y', 'TRUE', '1'] else 'NO'
                
                # Validate bundle quantities
                if str(row['Bundle']).upper() in ['YES', 'Y', 'TRUE', '1']:
                    max_stack_height = dimensions[2] / float(row['Height'])
                    if row['Quantity'] > max_stack_height * 3:
                        warnings.append(
                            f"Warning: Bundle quantity ({row['Quantity']}) for {row['Name']} "
                            f"may be too large for container height {dimensions[2]}m. "
                            "Consider splitting into smaller bundles."
                        )
                
                # Create item with validated dimensions and defaults
                bundle_value = str(row['Bundle']).upper() in ['YES', 'Y', 'TRUE', '1']
                
                # Get temperature sensitivity if available
                temp_sensitivity = None
                if temp_sensitivity_col and temp_sensitivity_col in row:
                    temp_sensitivity = str(row[temp_sensitivity_col]) if not pd.isna(row[temp_sensitivity_col]) else None
                
                item = Item(
                    name=str(row['Name']),
                    length=min(float(row['Length']), dimensions[0]),
                    width=min(float(row['Width']), dimensions[1]),
                    height=min(float(row['Height']), dimensions[2]),
                    weight=float(row['Weight']),
                    quantity=int(row['Quantity']),
                    fragility=str(row['Fragility']).upper(),
                    stackable=stackable_value,
                    boxing_type=str(row['BoxingType']),
                    bundle=bundle_value,
                    temperature_sensitivity=temp_sensitivity
                )
                items.append(item)
                current_app.logger.debug(f"Successfully processed item: {row['Name']}")
                
            except Exception as e:
                current_app.logger.error(f"Error processing item {row['Name']}: {str(e)}")
                warnings.append(f"Warning: Skipped item {row['Name']} due to error: {str(e)}")
                continue
        
        if not items:
            current_app.logger.error("No valid items found in CSV")
            current_app.logger.debug(f"CSV Preview:\n{df.head()}")
            return jsonify({
                'error': 'No valid items found in CSV',
                'details': 'Please ensure all required fields are present and valid',
                'preview': df.head().to_dict('records')
            }), 400
        
        # Log item info
        current_app.logger.info(f"Created {len(items)} items for packing")
        
        # Pack items
        current_app.logger.info("Starting container packing algorithm")

        # Add option to use genetic algorithm with LLM
        use_genetic = request.form.get('use_genetic', 'false').lower() == 'true'

        if use_genetic:
            current_app.logger.info("Using genetic algorithm with LLM adaptive mutation")
            from optigenix_module.optimization.genetic import optimize_packing_with_genetic_algorithm
            optimized_container = optimize_packing_with_genetic_algorithm(
                items, 
                dimensions,
                population_size=20,  # Smaller for testing
                generations=30       # Fewer generations for testing
            )
            # Replace the container with our optimized one
            container = optimized_container
        else:
            # Use regular packing algorithm with route temperature
            container.pack_items(items, route_temperature)
        
        current_app.logger.info(f"Packing complete - {len(container.items)} items packed")
        
        # Store container and generate report
        container_storage.current_container = container
        
        # Convert numpy arrays to lists for JSON serialization
        report_data = {
            'container_dims': list(dimensions),
            'volume_utilization': float(container.volume_utilization),
            'items_packed': len(container.items),
            'total_items': len(items),
            'remaining_volume': float(container.remaining_volume),
            'center_of_gravity': [float(x) for x in container.center_of_gravity],
            'total_weight': float(container.total_weight)
        }
        
        container_storage.current_report = report_data
        
        # Save the final plan as JSON
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        plan_filename = f"container_plan_{timestamp}.json"
        plan_filepath = os.path.join(PLANS_FOLDER, plan_filename)
        
        # Prepare the container data for JSON serialization
        plan_data = {
            'timestamp': timestamp,
            'container_info': container_info,
            'container_dimensions': list(dimensions),
            'statistics': report_data,
            'packed_items': [
                {
                    'name': item.name,
                    'position': [float(p) for p in item.position],
                    'dimensions': [float(d) for d in item.dimensions],
                    'weight': float(item.weight),
                    'fragility': item.fragility,
                    'stackable': item.stackable,
                    'boxing_type': item.boxing_type,
                    'bundle': item.bundle,
                    'temperature_sensitivity': getattr(item, 'temperature_sensitivity', None),
                    'needs_insulation': getattr(item, 'needs_insulation', False)
                } for item in container.items
            ],
            'unpacked_items': [
                {
                    'name': item.name,
                    'dimensions': [float(d) for d in item.dimensions],
                    'weight': float(item.weight),
                    'fragility': item.fragility,
                    'stackable': item.stackable,
                    'boxing_type': item.boxing_type,
                    'bundle': item.bundle,
                    'temperature_sensitivity': getattr(item, 'temperature_sensitivity', None),
                    'reason': reason
                } for item_name, (reason, item) in container.unpacked_reasons.items()
            ]
        }
        
        # Save the plan as JSON
        with open(plan_filepath, 'w') as f:
            json.dump(plan_data, f, indent=4)
            
        current_app.logger.info(f"Container plan saved to {plan_filepath}")
        
        # Create visualization with container info
        current_app.logger.info("Creating visualization")
        fig = create_interactive_visualization(container, container_info)
        
        return render_template('results.html',
                             plot=fig.to_html(),
                             container=container,
                             container_info=container_info,
                             report=report_data,
                             warnings=warnings)
                             
    except ValueError as e:
        current_app.logger.error(f"Value error: {str(e)}")
        return jsonify({'error': f'Invalid value in input: {str(e)}'}), 400
    except pd.errors.EmptyDataError:
        current_app.logger.error("Empty CSV file")
        return jsonify({'error': 'The uploaded CSV file is empty'}), 400
    except pd.errors.ParserError as e:
        current_app.logger.error(f"CSV parsing error: {str(e)}")
        return jsonify({'error': 'Unable to parse CSV file. Please check the format'}), 400
    except Exception as e:
        current_app.logger.error(f'Unexpected error during optimization: {str(e)}', exc_info=True)
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

def download_report_handler():
    """Handle the download report route"""
    if container_storage.current_container is None:
        return jsonify({'error': 'No container data available'})
    
    try:
        container = container_storage.current_container
        report = generate_detailed_report(container)
        
        # Generate both JSON and HTML reports
        if request.args.get('format') == 'json':
            buffer = BytesIO()
            json.dump(report, buffer, indent=4)
            buffer.seek(0)
            return send_file(
                buffer,
                as_attachment=True,
                download_name='packing_report.json',
                mimetype='application/json'
            )
        else:
            return render_template('downloadable_report.html',
                                report=report,
                                container=container)
    except Exception as e:
        return jsonify({'error': f'Error generating report: {str(e)}'})

def generate_alternative_handler():
    """Handle the alternative arrangement generation route"""
    if container_storage.current_container is None:
        return jsonify({'error': 'No container data available'})
    
    container_storage.current_container.generate_alternative_arrangement()
    fig = create_interactive_visualization(container_storage.current_container)
    
    return jsonify({
        'plot': fig.to_html(),
        'stats': {
            'utilization': container_storage.current_container.volume_utilization,
            'items_packed': len(container_storage.current_container.items),
            'remaining_volume': container_storage.current_container.remaining_volume
        }
    })

def view_report_handler():
    """Handle the view report route"""
    if container_storage.current_container is None:
        return jsonify({'error': 'No container data available'})
        
    container = container_storage.current_container
    report = generate_detailed_report(container)
    
    return render_template('report.html', 
                         report=report,
                         container=container)

def preview_csv_handler():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
        
    if file:
        try:
            # First try UTF-8
            content = file.read()
            file.seek(0)  # Reset file pointer
            
            # Try different encodings if UTF-8 fails
            encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    # For CSV files
                    if file.filename.endswith('.csv'):
                        decoded_content = content.decode(encoding)
                        csv_data = list(csv.reader(decoded_content.splitlines()))
                        # Process the CSV data
                        # ...
                        return jsonify({
                            'success': True,
                            'data': csv_data[:10],  # First 10 rows
                            'header': csv_data[0] if csv_data else [],
                            'encoding_used': encoding
                        })
                    # For Excel files
                    elif file.filename.endswith(('.xlsx', '.xls')):
                        # Excel handling code
                        # ...
                        pass
                except UnicodeDecodeError:
                    continue
            
            # If we get here, all encodings failed
            return jsonify({'error': 'Could not decode file with any supported encoding'})
            
        except Exception as e:
            return jsonify({'error': f'Error processing file: {str(e)}'})

def get_container_stats_handler():
    """Handle the container stats API endpoint"""
    if container_storage.current_container is None:
        return jsonify({'error': 'No container data available'}), 404
        
    container = container_storage.current_container
    return jsonify({
        'dimensions': container.dimensions,
        'volume_utilization': container.volume_utilization,
        'items_packed': len(container.items),
        'total_weight': container.total_weight,
        'center_of_gravity': container.center_of_gravity,
        'weight_balance_score': container._calculate_weight_balance_score(),
        'interlocking_score': container._calculate_interlocking_score()
    })

def get_item_details_handler(item_name):
    """Handle the item details API endpoint"""
    if container_storage.current_container is None:
        return jsonify({'error': 'No container data available'}), 404
        
    container = container_storage.current_container
    
    # Search for item in packed items
    for item in container.items:
        if item.name == item_name:
            return jsonify({
                'name': item.name,
                'position': item.position,
                'dimensions': item.dimensions,
                'weight': item.weight,
                'fragility': item.fragility,
                'stackable': item.stackable,
                'boxing_type': item.boxing_type,
                'bundle': item.bundle,
                'temperature_sensitivity': getattr(item, 'temperature_sensitivity', None),
                'needs_insulation': getattr(item, 'needs_insulation', False)
            })
            
    # Search in unpacked items
    if item_name in container.unpacked_reasons:
        reason, item = container.unpacked_reasons[item_name]
        return jsonify({
            'name': item.name,
            'dimensions': item.dimensions,
            'weight': item.weight,
            'fragility': item.fragility,
            'stackable': item.stackable,
            'boxing_type': item.boxing_type,
            'bundle': item.bundle,
            'temperature_sensitivity': getattr(item, 'temperature_sensitivity', None),
            'needs_insulation': getattr(item, 'needs_insulation', False),
            'unpacked_reason': reason
        })
        
    return jsonify({'error': 'Item not found'}), 404

def get_container_status_handler():
    """Handle the container status route"""
    if container_storage.current_container is None:
        return jsonify({
            'status': 'no_container',
            'message': 'No container has been optimized yet'
        })
    
    container = container_storage.current_container
    return jsonify({
        'status': 'ready',
        'utilization': container.volume_utilization,
        'items_packed': len(container.items),
        'unpacked_items': len(container.unpacked_reasons)
    })

def clear_container_handler():
    """Handle the clear container route"""
    container_storage.current_container = None
    container_storage.current_report = None
    return jsonify({'status': 'cleared'})

def handle_socketio_update_request():
    """Handle SocketIO update request"""
    if container_storage.current_container:
        fig = create_interactive_visualization(container_storage.current_container)
        return {
            'utilization': container_storage.current_container.volume_utilization,
            'items_packed': len(container_storage.current_container.items),
            'visualization': fig.to_json()
        }
    return None

def generate_alternative_plan_handler():
    """Handle the alternative plan generation route"""
    if container_storage.current_container is None:
        return jsonify({'error': 'No container data available'})
    
    try:
        # Generate multiple arrangements
        arrangements = container_storage.current_container.generate_multiple_arrangements(5)
        
        if not arrangements:
            return jsonify({'error': 'Could not generate alternative arrangements'})
        
        # Format results
        alternatives = []
        for container, score in arrangements:
            fig = create_interactive_visualization(container)
            alternatives.append({
                'plot': fig.to_html(),
                'stats': {
                    'utilization': f"{container.volume_utilization:.1f}",
                    'items_packed': len(container.items),
                    'remaining_volume': f"{container.remaining_volume:.2f}",
                    'interlocking_score': f"{container._calculate_interlocking_score():.2f}",
                    'space_efficiency': f"{(1 - (container.remaining_volume / container.total_volume)) * 100:.1f}",
                    'quality_score': f"{score:.2f}"
                }
            })
        
        return jsonify({
            'success': True,
            'alternatives': alternatives
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating alternative plans: {str(e)}")
        return jsonify({
            'error': 'Failed to generate alternative arrangements',
            'details': str(e)
        }), 500

# Add a route for Excel template download in your handlers.py
@bp.route('/static/templates/template.xlsx')
def serve_excel_template():
    # Create an Excel template file or serve a pre-made one
    return send_file(
        'static/templates/template.xlsx',
        as_attachment=True,
        download_name='template.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

def format_transport_modes():
    """Format transport modes data for frontend"""
    modes = []
    for mode_id, (mode_name, containers) in TRANSPORT_MODES.items():
        container_list = []
        for container_name in containers:
            if container_name in CONTAINER_TYPES:
                dims = CONTAINER_TYPES[container_name]
                container_list.append({
                    'name': container_name,
                    'dimensions': list(dims)
                })
        modes.append({
            'id': mode_id,
            'name': mode_name,
            'containers': container_list
        })
    return modes

def index():
    """Handle the index route"""
    data = {
        'transport_modes': format_transport_modes()
    }
    return render_template('index.html', data=data)