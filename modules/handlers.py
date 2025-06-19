"""
Route handler functions for the container packing application
"""
from flask import request, render_template, send_file, jsonify, Blueprint, current_app
from werkzeug.utils import secure_filename
import pandas as pd
from io import BytesIO
import csv
import subprocess
import sys

# Import from config instead of app_modular
from config import PLANS_FOLDER

import json
import datetime
import os

# Import directly from the new optigenix_module structure
from optigenix_module.constants import CONTAINER_TYPES, TRANSPORT_MODES, get_predefined_container_dimensions
from optigenix_module.models.item import Item
from optigenix_module.models.container import EnhancedContainer
from optigenix_module.optimization.genetic import optimize_packing_with_genetic_algorithm # Add this line

from modules.models import ContainerStorage
from modules.visualization import create_interactive_visualization
from modules.report import generate_detailed_report
from modules.utils import allowed_file, cleanup_old_files

# Create a blueprint
bp = Blueprint('handlers', __name__)

# Create container storage
container_storage = ContainerStorage()

def landing_handler():
    """Handle the landing page route"""
    return render_template('landing.html')

def start_handler():
    """Handle the start page route"""
    # Format transport modes using the shared function
    formatted_modes = format_transport_modes()
    
    # Ensure Road Transport mode has all container types as specified in constants.py
    road_transport = next((mode for mode in formatted_modes if mode['id'] == '1'), None)
    if road_transport:
        expected_containers = TRANSPORT_MODES['1'][1]  # Get from constants
        current_containers = [c['name'] for c in road_transport['containers']]
        
        # Check if any container is missing
        missing_containers = [c for c in expected_containers if c not in current_containers]
        if missing_containers:
            print(f"WARNING: Missing container types for Road Transport: {missing_containers}")
            # Add missing containers to the formatted modes
            for container_name in missing_containers:
                if container_name in CONTAINER_TYPES:
                    dims = CONTAINER_TYPES[container_name]
                    road_transport['containers'].append({
                        'name': container_name,
                        'dimensions': dims[:3],  # First 3 values are dimensions (L,W,H)
                        'volume': dims[0] * dims[1] * dims[2],  # Calculate volume
                        'max_weight': dims[3] if len(dims) > 3 else 30000  # Include max weight if available
                    })
    
    # Debug before sending to frontend
    print("DEBUG: Transport modes to be sent to frontend:")
    for mode in formatted_modes:
        print(f"  {mode['name']}: {len(mode['containers'])} container types - {[c['name'] for c in mode['containers']]}")
    
    # Add default data for JavaScript
    default_data = {
        'transport_modes': formatted_modes,
        'container_types': CONTAINER_TYPES
    }

    # Debug output to verify data
    print("Transport modes prepared for frontend:", len(formatted_modes))
    for mode in formatted_modes:
        print(f"- {mode['name']}: {len(mode['containers'])} containers")
    
    return render_template('index.html', data=default_data)

def optimize_handler():
    """Handle the optimize route"""
    if request.method == 'POST':
        try:
            # Enable debug logging
            current_app.logger.info("=== OPTIMIZE ROUTE CALLED ===")
            current_app.logger.info(f"Request form keys: {list(request.form.keys())}")
            current_app.logger.info(f"Request files: {list(request.files.keys())}")
            
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
            
            current_app.logger.info(f"Received - Transport mode: {transport_mode}, Container type: {container_type}")
            
            # Validate transport mode
            if not transport_mode or transport_mode not in TRANSPORT_MODES:
                current_app.logger.error(f"Invalid transport mode: {transport_mode}")
                return jsonify({'error': 'Invalid transport mode selected'}), 400
            
            # Create container_info dictionary with corrected mapping
            transport_mode_names = {
                '1': 'Road Transport',
                '2': 'Sea Transport', 
                '3': 'Air Transport',
                '4': 'Rail Transport',
                '5': 'Custom'
            }
            
            container_info = {
                'type': container_type if transport_mode != '5' else 'Custom',
                'transport_mode': transport_mode_names.get(transport_mode, 'Unknown'),
                'transport_mode_id': transport_mode
            }
            
            current_app.logger.info(f"Container info: {container_info}")
            
            # Try to get dimensions from predefined containers first
            dimensions = get_predefined_container_dimensions(container_type)
            
            if dimensions is None:
                # If not found, try to parse custom dimensions
                try:
                    dimensions = [
                        float(request.form.get('length', 0)),
                        float(request.form.get('width', 0)),
                        float(request.form.get('height', 0))
                    ]
                    if any(d <= 0 for d in dimensions):
                        raise ValueError("All dimensions must be positive")
                    current_app.logger.info(f"Custom dimensions: {dimensions}")
                except (ValueError, KeyError) as e:
                    current_app.logger.error(f"Error with container dimensions: {str(e)}")
                    return jsonify({'error': f'Invalid container dimensions: {str(e)}'}), 400
            else:
                current_app.logger.info(f"Predefined container '{container_type}' dimensions: {dimensions}")
            
            # Log the dimensions to help debug
            current_app.logger.info(f"Final container dimensions: {dimensions}")
            
            # Save and process file with proper path normalization
            filename = secure_filename(file.filename)
            filepath = os.path.normpath(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            
            # Ensure upload directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save file with normalized path
            file.save(filepath)
            
            current_app.logger.info(f"File saved at: {filepath}")
            
            # Load data into pandas DataFrame (df)
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
                    
                    # FIXED: Explicitly set route temperature as environment variable for both normal and LLM versions
                    os.environ["ROUTE_TEMPERATURE"] = str(route_temperature)
                    current_app.logger.info(f"Set ROUTE_TEMPERATURE={route_temperature} environment variable")
                except ValueError:
                    current_app.logger.warning(f"Invalid route temperature: {request.form['route_temperature']}")            # Get genetic algorithm parameters with sensible defaults
            population_size = 10  # Default if not specified by user
            num_generations = 8  # Default if not specified by user
            
            # Get dataset size to log info
            total_items = sum(int(row['Quantity']) for _, row in df.iterrows())
            current_app.logger.info(f"Dataset contains {total_items} total items")
            
            optimization_algorithm = request.form.get('optimization_algorithm') # Ensure this is defined before use

            # >>> This is the crucial block for defining 'items' <<<
            items = [] 
            warnings = []
            for index, row in df.iterrows():
                try:
                    # Handle potential missing 'Bundle' column gracefully
                    bundle_value_raw = row.get('Bundle', 'NO') # Default to 'NO' if 'Bundle' column is missing
                    bundle_value = str(bundle_value_raw).upper() == 'YES'

                    # Handle potential missing temperature sensitivity column
                    temp_sensitivity = None
                    if temp_sensitivity_col and temp_sensitivity_col in row and pd.notna(row[temp_sensitivity_col]):
                        temp_sensitivity = str(row[temp_sensitivity_col])
                    
                    # Handle stackable column
                    stackable_value = 'NO' # Default
                    if stackable_col and stackable_col in row and pd.notna(row[stackable_col]):
                        stackable_raw = str(row[stackable_col]).upper()
                        if stackable_raw in ['YES', 'TRUE', '1']:
                            stackable_value = 'YES'
                        elif stackable_raw in ['NO', 'FALSE', '0']:
                            stackable_value = 'NO'
                        # else keep default 'NO' or add more specific handling

                    item = Item(
                        name=str(row['Name']),
                        length=float(row['Length']),
                        width=float(row['Width']),
                        height=float(row['Height']),
                        weight=float(row['Weight']),
                        quantity=int(row['Quantity']),
                        fragility=str(row['Fragility']),
                        stackable=stackable_value,
                        boxing_type=str(row['BoxingType']),
                        bundle=bundle_value,
                        temperature_sensitivity=temp_sensitivity
                    )
                    items.append(item)
                    current_app.logger.debug(f"Successfully processed item: {row['Name']}")
                    
                except Exception as e:
                    current_app.logger.error(f"Error processing item {row['Name']} at index {index}: {str(e)}")
                    warnings.append(f"Warning: Skipped item {row['Name']} (row {index+2}) due to error: {str(e)}")
                    continue
            
            if not items:
                current_app.logger.error("No valid items could be processed from the uploaded file.")
                # It's better to return a JSON error here if no items are processed
                return jsonify({
                    'error': 'No valid items could be processed from the uploaded file.',
                    'details': 'Please check the file format and data. Warnings: ' + "; ".join(warnings)
                }), 400

            current_app.logger.info(f"Successfully created {len(items)} Item objects for packing.")


            if 'population_size' in request.form and request.form['population_size']:
                try:
                    population_size = int(request.form['population_size'])
                    current_app.logger.info(f"Using population size: {population_size}")
                except ValueError:
                    current_app.logger.warning(f"Invalid population size: {request.form['population_size']}")
            
            if 'num_generations' in request.form and request.form['num_generations']:
                try:
                    num_generations = int(request.form['num_generations'])
                    current_app.logger.info(f"Using number of generations: {num_generations}")
                except ValueError:
                    current_app.logger.warning(f"Invalid number of generations: {request.form['num_generations']}")

            # Get constraint weights from form - convert form names to expected backend names
            constraint_weights = {
                'volume_utilization_weight': float(request.form.get('volume_weight', 0.75)),
                'stability_score_weight': float(request.form.get('stability_weight', 0.5)),
                'contact_ratio_weight': float(request.form.get('contact_weight', 0.5)),
                'weight_balance_weight': float(request.form.get('balance_weight', 0.25)),
                'items_packed_ratio_weight': float(request.form.get('items_packed_weight', 0.25)),
                'temperature_constraint_weight': float(request.form.get('temperature_weight', 0.3)),
                'weight_capacity_weight': float(request.form.get('weight_capacity', 0.5))
            }
            
            # Normalize weights
            total_weight_sum = sum(constraint_weights.values())
            normalized_weights = {k: v / total_weight_sum if total_weight_sum > 0 else 0 for k, v in constraint_weights.items()}
            current_app.logger.info(f"Normalized constraint weights: {json.dumps(normalized_weights, indent=2)}")

            # Initialize the container object with its dimensions
            container = EnhancedContainer(dimensions)

            # The 'items' variable is now defined before this block
            if optimization_algorithm == 'genetic':
                current_app.logger.info("Using AI Enhanced Genetic Algorithm")
                # Ensure items are correctly prepared for the genetic algorithm
                
                # Pass the normalized_weights from UI sliders as fitness_weights
                # Use the correctly parsed population_size and num_generations
                optimized_container_result = optimize_packing_with_genetic_algorithm(
                    items,
                    dimensions,
                    population_size=population_size, # Use the variable defined above
                    generations=num_generations,   # Use the variable defined above
                    route_temperature=route_temperature,
                    fitness_weights=normalized_weights 
                )
                # Assuming optimize_packing_with_genetic_algorithm returns the container object
                # or a structure from which the container can be accessed.
                # For now, let's assume it returns the container directly or as part of a tuple.
                if isinstance(optimized_container_result, tuple): # e.g. (container, best_fitness, gen_count)
                    container = optimized_container_result[0] 
                else: # Assuming it returns just the container
                    container = optimized_container_result

            else:
                current_app.logger.info("Using Regular Packing Algorithm")
                # Use regular packing algorithm with route temperature AND constraint weights
                # The container object was already initialized earlier.
                container.pack_items(items, route_temperature, constraint_weights=constraint_weights)
                current_app.logger.info("Regular packing algorithm complete")
            
            current_app.logger.info(f"Packing complete - {len(container.items)} items packed into the container.")
            
            # Store container and generate report
            container_storage.current_container = container            # Convert numpy arrays to lists for JSON serialization            # FIXED: Proper item counting for genetic algorithm
            if optimization_algorithm == 'genetic' and hasattr(container, 'unpacked_items'):
                # For genetic algorithm: count actual expanded items from original data
                packed_boxes = len(container.items)
                unpacked_items_count = len(getattr(container, 'unpacked_items', []))
                
                # Calculate the correct total based on actual item expansion logic
                total_expanded_items = 0
                for item in items:
                    quantity = getattr(item, 'quantity', 1)
                    is_bundled = getattr(item, 'bundle', 'NO') == 'YES'
                    
                    if quantity > 1 and not is_bundled:
                        # Non-bundled items are expanded to individual items
                        total_expanded_items += quantity
                    else:
                        # Bundled items or single items count as 1
                        total_expanded_items += 1                
                # Calculate bundle vs individual breakdown for clearer reporting
                total_csv_rows = len(items)  # CSV rows
                total_raw_quantity = sum(int(row['Quantity']) for _, row in df.iterrows())
                bundled_count = sum(1 for _, row in df.iterrows() if str(row.get('Bundle', 'NO')).upper() == 'YES')
                individual_expanded = sum(int(row['Quantity']) for _, row in df.iterrows() if str(row.get('Bundle', 'NO')).upper() == 'NO')
                
                current_app.logger.info(f"Genetic Algorithm Results:")
                current_app.logger.info(f"  CSV rows processed: {total_csv_rows}")
                current_app.logger.info(f"  Total raw quantity: {total_raw_quantity} pieces")
                current_app.logger.info(f"  After bundling logic: {bundled_count} bundles + {individual_expanded} individuals = {total_expanded_items} items")
                current_app.logger.info(f"  Packed: {packed_boxes}, Unpacked: {unpacked_items_count}")
                current_app.logger.info(f"  Success rate: {packed_boxes}/{total_expanded_items} = {(packed_boxes/total_expanded_items*100):.1f}%")
                
                # Use expanded counts for reporting
                packed_items_count = packed_boxes
                total_items_for_report = total_expanded_items
            else:
                # For regular algorithm: use original logic
                total_unique_items = len(items)
                packed_boxes = len(container.items)
                unpacked_items_count = len(getattr(container, 'unpacked_reasons', {}))
                packed_items_count = packed_boxes
                total_items_for_report = total_unique_items
                
                current_app.logger.info(f"Regular Algorithm Results:")
                current_app.logger.info(f"  Total items: {total_unique_items}, Packed: {packed_items_count}, Unpacked: {unpacked_items_count}")

            report_data = {
                'container_dims': list(dimensions),
                'volume_utilization': float(container.volume_utilization * 100),  # Multiply by 100 to get percentage value
                'items_packed': packed_items_count,
                'total_items': total_items_for_report,
                'remaining_volume': float(container.remaining_volume),
                'center_of_gravity': [float(x) for x in container.center_of_gravity],
                'total_weight': float(container.total_weight),
                'best_fitness': getattr(container, 'best_fitness', 0.0),
                'generation_count': getattr(container, 'generation_count', 0),
                'algorithm_used': 'Genetic Algorithm' if optimization_algorithm == 'genetic' else 'Regular Algorithm'
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
                'best_fitness': getattr(container, 'best_fitness', 0.0),
                'generation_count': getattr(container, 'generation_count', 0),
                'algorithm_used': 'Genetic Algorithm' if optimization_algorithm == 'genetic' else 'Regular Algorithm',
                'optimization_method': 'genetic' if optimization_algorithm == 'genetic' else 'regular',
                'best_fitness': getattr(container, 'best_fitness', 0.0),
                'generation_count': getattr(container, 'generation_count', 0),
                'algorithm_used': 'Genetic Algorithm' if optimization_algorithm == 'genetic' else 'Regular Algorithm',
                'optimization_method': 'genetic' if optimization_algorithm == 'genetic' else 'regular',
                'best_fitness': getattr(container, 'best_fitness', 0.0),
                'generation_count': getattr(container, 'generation_count', 0),
                'algorithm_used': 'Genetic Algorithm' if optimization_algorithm == 'genetic' else 'Regular Algorithm',
                'optimization_method': 'genetic' if optimization_algorithm == 'genetic' else 'regular',
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
                        'needs_insulation': getattr(item, 'needs_insulation', False),
                        'reason': reason
                    } for item_name, (reason, item) in container.unpacked_reasons.items()
                ] + [
                    # Include unpacked items from genetic algorithm if available
                    {
                        'name': item.name,
                        'dimensions': [float(d) for d in item.dimensions],
                        'weight': float(item.weight),
                        'fragility': getattr(item, 'fragility', 'UNKNOWN'),
                        'stackable': getattr(item, 'stackable', 'UNKNOWN'),
                        'boxing_type': getattr(item, 'boxing_type', 'UNKNOWN'),
                        'bundle': getattr(item, 'bundle', False),
                        'temperature_sensitivity': getattr(item, 'temperature_sensitivity', None),
                        'reason': "Failed to place item with genetic algorithm - Try adjusting algorithm parameters"
                    } for item in getattr(container, 'unpacked_items', [])
                ]
            }
            
            # Save the plan as JSON
            with open(plan_filepath, 'w') as f:
                json.dump(plan_data, f, indent=4)
                
            current_app.logger.info(f"Container plan saved to {plan_filepath}")
              # Create visualization with container info
            current_app.logger.info("Creating visualization")
            fig = create_interactive_visualization(container, container_info)
              # Calculate item counts by category (boxing_type)
            category_counts = {}
            for item in container.items:
                category = getattr(item, 'boxing_type', 'Other') # Use 'Other' if boxing_type is missing
                category_counts[category] = category_counts.get(category, 0) + 1
            
            current_app.logger.info(f"Calculated category counts: {category_counts}")
            
            # Run standalone_visualization.py in background
            try:
                current_app.logger.info("Starting standalone_visualization.py...")
                visualization_script = os.path.join(os.getcwd(), "standalone_visualization.py")
                subprocess.Popen([sys.executable, visualization_script], 
                               cwd=os.getcwd(),
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                current_app.logger.info("standalone_visualization.py started successfully")
            except Exception as e:
                current_app.logger.warning(f"Failed to start standalone_visualization.py: {e}")
            
            return render_template('container_visualization.html',
                                 plot=fig.to_html(),
                                 container=container,
                                 container_info=container_info,
                                 report=report_data,
                                 warnings=warnings,
                                 category_counts=category_counts) # Pass category_counts to template
        except ValueError as e:
            current_app.logger.error(f"Value error: {str(e)}")
            return jsonify({'error': f'Invalid value in input: {str(e)}'}), 400
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
    """Handle CSV preview file upload"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'})
        
    if file:
        try:
            # First try UTF-8
            content = file.read()
            file.seek(0)  # Reset file pointer
            
            # Try different encodings if UTF-8 fails
            encodings = ['utf-8', 'latin-1', 'iso-8859-1']
            df = None
            
            for encoding in encodings:
                try:
                    if file.filename.endswith('.csv'):
                        df = pd.read_csv(file, encoding=encoding, nrows=10)  # Show more rows for preview
                    elif file.filename.endswith(('.xlsx', '.xls')):
                        df = pd.read_excel(file, nrows=10)
                    break
                except UnicodeDecodeError:
                    file.seek(0)  # Reset file pointer
                    continue
                except Exception as e:
                    return jsonify({'success': False, 'error': f'Error reading file: {str(e)}'})
            
            if df is None:
                return jsonify({'success': False, 'error': 'Could not decode file with any supported encoding'})
                
            # Convert rows to list of dictionaries for easier frontend handling
            preview_rows = df.to_dict('records')
            
            preview_data = {
                'success': True,
                'columns': df.columns.tolist(),
                'preview': preview_rows,
                'total_rows': len(df),
                'items_count': len(df)
            }
            
            return jsonify(preview_data)
            
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error processing file: {str(e)}'})
    
    return jsonify({'success': False, 'error': 'No file provided'})

def get_container_stats_handler():
    """Handle the container stats API endpoint"""
    if container_storage.current_container is None:
        return jsonify({'error': 'No container data available'}), 404
        
    container = container_storage.current_container
    return jsonify({
        'dimensions': container.dimensions,
        'volume_utilization': container.volume_utilization * 100,  # Convert to percentage for frontend
        'items_packed': len(container.items),
        'total_weight': container.total_weight,
        'center_of_gravity': container.center_of_gravity,
        'weight_balance_score': container._calculate_weight_balance_score(),
        'interlocking_score': container._calculate_interlocking_score()
    })

def get_item_details_handler(item_name):
    """Handle the item details API endpoint"""
    if container_storage.current_container is None:
        return jsonify({'error': 'No container data available'})
        
    container = container_storage.current_container
    
    # Search for item in packed items
    for item in container.items:
        if item.name == item_name:
            return jsonify({
                'name': item.name,
                'position': [float(p) for p in item.position],
                'dimensions': [float(d) for d in item.dimensions],
                'weight': float(item.weight),
                'fragility': item.fragility,
                'stackable': item.stackable,
                'boxing_type': item.boxing_type,
                'bundle': item.bundle,
                'temperature_sensitivity': getattr(item, 'temperature_sensitivity', None),
                'needs_insulation': getattr(item, 'needs_insulation', False),
                'is_packed': True
            })
            
    # Search in unpacked items
    if item_name in container.unpacked_reasons:
        reason, item = container.unpacked_reasons[item_name]
        return jsonify({
            'name': item.name,
            'dimensions': [float(d) for d in item.dimensions],
            'weight': float(item.weight),
            'fragility': item.fragility,
            'stackable': item.stackable,
            'boxing_type': item.boxing_type,
            'bundle': item.bundle,
            'temperature_sensitivity': getattr(item, 'temperature_sensitivity', None),
            'needs_insulation': getattr(item, 'needs_insulation', False),
            'is_packed': False,
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
        'utilization': container.volume_utilization * 100,  # Convert to percentage for frontend
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
            return jsonify({
                'success': False,
                'error': 'Could not generate alternative arrangements'
            })
        
        # Format results
        alternatives = []
        for container, score in arrangements:
            alternative = {
                'score': float(score),
                'volume_utilization': float(container.volume_utilization * 100),
                'items_packed': len(container.items),
                'total_weight': float(container.total_weight),
                'stability_score': float(container._calculate_stability_score()),
                'weight_balance': float(container._calculate_weight_balance_score())
            }
            alternatives.append(alternative)
        
        return jsonify({
            'success': True,
            'alternatives': alternatives
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating alternative plans: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error generating alternative plans: {str(e)}'
        })

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
    """Format transport modes data for frontend with corrected mapping"""
    # Updated mapping to match the corrected HTML data-value attributes
    transport_mode_mapping = {
        '1': 'Road Transport',  # Truck
        '2': 'Sea Transport',   # Ship  
        '3': 'Air Transport',   # Plane
        '4': 'Rail Transport',  # Train
        '5': 'Custom'          # Custom
    }
    
    modes = []
    for mode_id, mode_name in transport_mode_mapping.items():
        if mode_id in TRANSPORT_MODES:
            _, containers = TRANSPORT_MODES[mode_id]
            container_list = []
            
            # Debug logging
            current_app.logger.debug(f"Processing {mode_name} (ID: {mode_id}) with containers: {containers}")
                
            for container_name in containers:
                if container_name in CONTAINER_TYPES:
                    dims = CONTAINER_TYPES[container_name]
                    container_list.append({
                        'name': container_name,
                        'dimensions': dims[:3],  # First 3 values are dimensions (L,W,H)
                        'volume': dims[0] * dims[1] * dims[2],  # Calculate volume
                        'max_weight': dims[3] if len(dims) > 3 else 30000  # Include max weight if available
                    })
                else:
                    current_app.logger.warning(f"Container '{container_name}' not found in CONTAINER_TYPES")
            
            # Use display names
            display_name = "Truck" if mode_name == "Road Transport" else mode_name.replace(" Transport", "")
            
            modes.append({
                'id': mode_id,
                'name': display_name,
                'containers': container_list
            })
            
            current_app.logger.debug(f"Added mode: {display_name} with {len(container_list)} containers")
    
    return modes

def index():
    """Handle the index route"""
    data = {
        'transport_modes': format_transport_modes()
    }
    return render_template('index.html', data=data)