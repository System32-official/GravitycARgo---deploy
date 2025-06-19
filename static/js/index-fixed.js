/**
 * GravitycARgo - Complete Container Optimization Application
 * Main script for index.html with all functionality corrected
 */

// Transport mode mapping
const transportModeMapping = {
  "1": "Truck",
  "2": "Ship", 
  "3": "Plane",
  "4": "Train",
  "5": "Custom"
};

document.addEventListener('DOMContentLoaded', function() {
  console.log("DOM fully loaded - initializing GravitycARgo application");
  
  // Debug information
  console.log("Starting debugging...");
  console.log("Current URL:", window.location.href);
  console.log("Document ready state:", document.readyState);
  
  // Initialize AOS animations
  AOS.init({
    offset: 100,
    duration: 600,
    easing: 'ease-in-out',
    once: true
  });

  // Initialize Locomotive Scroll for smooth scrolling
  const scroll = new LocomotiveScroll({
    el: document.querySelector('[data-scroll-container]'),
    smooth: true,
    smartphone: { smooth: false },
    tablet: { smooth: false }
  });
  // Get data passed from Flask
  const defaultData = JSON.parse(document.getElementById('flask-data').textContent || '{"transport_modes":[]}');
  
  console.log("All transport modes:", defaultData.transport_modes);
  defaultData.transport_modes.forEach(mode => {
    console.log(`${mode.name} has ${mode.containers ? mode.containers.length : 0} container types`);
  });

  // Initialize all variables in one place
  const fileInput = document.getElementById('file_input');
  const dropZone = document.getElementById('dropZone');
  const fileInfo = document.getElementById('file-info');
  const fileName = document.getElementById('fileName');
  const fileSize = document.getElementById('fileSize');
  const removeFile = document.getElementById('removeFile');
  const tempSlider = document.getElementById('temp_slider');
  const tempInput = document.getElementById('route_temperature');
  const transportMode = document.getElementById('transport_mode');
  const containerType = document.getElementById('container_type');
  const customDimensions = document.getElementById('custom_dimensions');
  const optimizerForm = document.getElementById('optimizerForm');
  const sections = document.querySelectorAll('.form-section');
  const steps = document.querySelectorAll('.step');
  const nextBtn = document.getElementById('next1');
  const prevBtn = document.getElementById('prev1');
  
  console.log("Form sections found:", sections.length);
  console.log("Navigation steps found:", steps.length);

  // 1. TRANSPORT MODE SELECTION
  const transportOptions = document.querySelectorAll(".transport-option");
  
  if (transportOptions.length > 0) {
    console.log("Found transport options:", transportOptions.length);

    transportOptions.forEach((option) => {
      option.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        
        console.log("Transport option clicked:", this.dataset.value);
        
        // Remove selected class from all options
        transportOptions.forEach((opt) => {
          opt.classList.remove("selected");
          opt.classList.remove("active");
        });

        // Add selected class to clicked option
        this.classList.add("selected");
        this.classList.add("active");

        // Set transport mode value
        const transportValue = this.getAttribute("data-value");
        if (transportMode) {
          transportMode.value = transportValue;
          console.log("Transport mode input set to:", transportValue);
        }

        // Enable next button
        if (nextBtn) {
          nextBtn.disabled = false;
          nextBtn.classList.remove("disabled");
        }

        // Handle container options display
        updateContainerDisplay(transportValue);
      });
    });
  } else {
    console.error("No transport options found in DOM");
  }

  // 2. CONTAINER SELECTION FUNCTIONS
  function updateContainerDisplay(transportModeValue) {
    console.log("Updating container display for mode:", transportModeValue);

    const containerOptions = document.getElementById("container_options");
    const customDimensions = document.getElementById("custom_dimensions");

    if (!containerOptions || !customDimensions) {
      console.error("Container display elements not found");
      return;
    }

    if (transportModeValue === "5") {
      // Custom container
      customDimensions.style.display = "block";
      containerOptions.style.display = "none";
      console.log("Showing custom dimensions form");
    } else {
      // Predefined containers
      customDimensions.style.display = "none";
      containerOptions.style.display = "block";
      loadContainerOptions(transportModeValue);
    }
  }

  function loadContainerOptions(transportModeValue) {
    console.log("Loading container options for transport mode:", transportModeValue);

    // Check if defaultData is available
    if (!defaultData || !defaultData.transport_modes) {
      console.error("Transport modes data not available");
      return;
    }

    // Find the transport mode data
    const transportModeData = defaultData.transport_modes.find(mode => mode.id === transportModeValue);
    
    if (!transportModeData) {
      console.error("Transport mode data not found for ID:", transportModeValue);
      return;
    }

    const containerGrid = document.getElementById("containerGrid");
    if (!containerGrid) {
      console.error("Container grid element not found");
      return;
    }

    containerGrid.innerHTML = "";

    transportModeData.containers.forEach((container) => {
      const containerCard = document.createElement("div");
      containerCard.className = "container-option";
      containerCard.setAttribute("data-container", container.name);
      containerCard.innerHTML = `
        <i class="fas fa-cube container-icon"></i>
        <div class="container-name">${container.name}</div>
        <div class="container-dims">${container.dimensions[0]}m × ${container.dimensions[1]}m × ${container.dimensions[2]}m</div>
        <div class="container-volume">${(container.dimensions[0] * container.dimensions[1] * container.dimensions[2]).toFixed(1)} m³</div>
        <div class="container-check">
          <i class="fas fa-check"></i>
        </div>
      `;

      containerCard.addEventListener("click", function () {
        document.querySelectorAll(".container-option").forEach((card) => {
          card.classList.remove("active");
          card.classList.remove("selected");
        });
        this.classList.add("active");
        this.classList.add("selected");
        
        if (containerType) {
          containerType.value = container.name;
        }
        console.log("Container selected:", container.name);
        
        // Update container visualization if available
        if (typeof updateContainerModel === 'function') {
          updateContainerModel(container.dimensions);
        }
      });

      containerGrid.appendChild(containerCard);
    });

    console.log("Added", transportModeData.containers.length, "container options");
  }

  // 3. TEMPERATURE SLIDER FUNCTIONALITY
  if (tempSlider && tempInput) {
    tempSlider.addEventListener('input', function() {
      const value = this.value;
      tempInput.value = value;
      
      // Update tooltip
      const tooltip = document.getElementById('tempTooltip');
      if (tooltip) {
        tooltip.textContent = `${value}°C`;
        // Calculate tooltip position
        const percentage = ((value - this.min) / (this.max - this.min)) * 100;
        tooltip.style.left = `${percentage}%`;
      }
      
      // Update slider background
      const percentage = ((value - this.min) / (this.max - this.min)) * 100;
      this.style.background = `linear-gradient(to right, var(--accent) 0%, var(--accent) ${percentage}%, #e0e0e0 ${percentage}%, #e0e0e0 100%)`;
      
      // Update temperature display
      const tempDisplay = document.getElementById('temp_display');
      if (tempDisplay) {
        tempDisplay.textContent = `${value}°C`;
        
        // Change color based on temperature
        if (value < 0) {
          tempDisplay.style.color = '#3b82f6'; // Cold blue
        } else if (value > 25) {
          tempDisplay.style.color = '#ef4444'; // Hot red
        } else {
          tempDisplay.style.color = '#10b981'; // Normal green
        }
      }

      // Trigger form validation
      if (optimizerForm) {
        optimizerForm.dispatchEvent(new Event('input'));
      }
    });
    
    // Set initial value
    if (tempInput.value) {
      tempSlider.value = tempInput.value;
      tempSlider.dispatchEvent(new Event('input'));
    }
  }

  // 4. CONSTRAINT SLIDERS FUNCTIONALITY
  const constraintSliders = document.querySelectorAll('.constraint-slider');
  const constraintPresets = document.querySelectorAll('.constraint-preset');
  
  // Preset configurations
  const presets = {
    balanced: {
      volume_weight: 50,
      stability_weight: 50,
      contact_weight: 50,
      balance_weight: 50,
      items_packed_weight: 50,
      temperature_weight: 30
    },
    volume: {
      volume_weight: 80,
      stability_weight: 30,
      contact_weight: 40,
      balance_weight: 20,
      items_packed_weight: 60,
      temperature_weight: 20
    },
    stability: {
      volume_weight: 40,
      stability_weight: 80,
      contact_weight: 60,
      balance_weight: 70,
      items_packed_weight: 30,
      temperature_weight: 40
    }
  };

  // Update slider value display
  function updateSliderValue(slider) {
    const value = slider.value;
    const valueDisplay = document.getElementById(`${slider.id}_value`);
    if (valueDisplay) {
      valueDisplay.textContent = `${value}%`;
    }
  }

  // Apply preset values
  function applyPreset(presetName) {
    const preset = presets[presetName];
    if (!preset) return;

    // Update all sliders with preset values
    Object.entries(preset).forEach(([key, value]) => {
      const slider = document.getElementById(key);
      if (slider) {
        slider.value = value;
        updateSliderValue(slider);
      }
    });

    // Update active state of preset buttons
    constraintPresets.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.preset === presetName);
    });
  }

  // Initialize sliders
  constraintSliders.forEach(slider => {
    // Set initial value display
    updateSliderValue(slider);

    // Add input event listener
    slider.addEventListener('input', () => {
      updateSliderValue(slider);
      
      // Remove active state from preset buttons when manually adjusting
      constraintPresets.forEach(btn => btn.classList.remove('active'));
    });
  });

  // Initialize preset buttons
  constraintPresets.forEach(btn => {
    btn.addEventListener('click', () => {
      const presetName = btn.dataset.preset;
      if (presetName) {
        applyPreset(presetName);
      }
    });
  });

  // 5. FILE UPLOAD FUNCTIONALITY
  if (fileInput) {
    fileInput.addEventListener("change", function () {
      if (this.files.length > 0) {
        const file = this.files[0];
        handleFile(file);
      }
    });
  }

  if (dropZone) {
    // Drag and drop functionality
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
      dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropZone.classList.remove('drag-over');
      if (e.dataTransfer.files.length) {
        handleFile(e.dataTransfer.files[0]);
      }
    });

    // Make the zone clickable to browse files
    const browseBtn = dropZone.querySelector('.browse-btn');
    if (browseBtn) {
      browseBtn.addEventListener('click', () => {
        if (fileInput) fileInput.click();
      });
    } else {
      dropZone.addEventListener('click', (e) => {
        if (e.target !== fileInput && !e.target.closest('.template-links')) {
          if (fileInput) fileInput.click();
        }
      });
    }
  }

  function handleFile(file) {
    if (!file) return;
    
    const validTypes = ['.csv', '.xlsx', '.xls'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    
    if (validTypes.includes(fileExt)) {
      if (fileName) fileName.textContent = file.name;
      if (fileSize) fileSize.textContent = formatFileSize(file.size);
      if (dropZone) dropZone.classList.add('file-dropped');
      if (fileInfo) fileInfo.style.display = 'block';
    } else {
      showError('Please upload a CSV or Excel file');
      if (fileInput) fileInput.value = '';
    }
  }
  
  function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }
  
  if (removeFile) {
    removeFile.addEventListener('click', () => {
      if (fileInput) fileInput.value = '';
      if (dropZone) dropZone.classList.remove('file-dropped');
      if (fileInfo) fileInfo.style.display = 'none';
    });
  }

  // 5. MULTI-STEP FORM NAVIGATION
  function updateStepNavigation() {
    const currentStepNum = Array.from(sections).findIndex(section => section.classList.contains('active')) + 1;
    
    if (currentStepNum === 1) {
      if (prevBtn) prevBtn.style.display = 'none';
      if (nextBtn) {
        nextBtn.style.display = 'block';
        nextBtn.innerHTML = '<i class="fas fa-arrow-right"></i> Next';
      }
    } else if (currentStepNum === 4) {
      if (prevBtn) prevBtn.style.display = 'block';
      if (nextBtn) {
        nextBtn.style.display = 'block';
        nextBtn.innerHTML = '<i class="fas fa-play"></i> Start Optimization';
      }
    } else {
      if (prevBtn) prevBtn.style.display = 'block';
      if (nextBtn) {
        nextBtn.style.display = 'block';
        nextBtn.innerHTML = '<i class="fas fa-arrow-right"></i> Next';
      }
    }
  }    // Update review summary with user selections
    function updateReviewSummary() {
        console.log('Updating review summary...');
        
        try {
            // Get transport mode
            const transportMode = getSelectedTransportMode();
            const transportElement = document.getElementById('reviewTransportMode');
            if (transportElement) {
                if (transportMode) {
                    const transportNames = {
                        '0': 'Truck',
                        '1': 'Ship', 
                        '2': 'Plane',
                        '3': 'Train',
                        '4': 'Custom'
                    };
                    transportElement.textContent = transportNames[transportMode] || 'Not selected';
                } else {
                    transportElement.textContent = 'Not selected';
                }
            }
            
            // Get container type
            const containerType = document.getElementById('container_type')?.value;
            const containerElement = document.getElementById('reviewContainerType');
            if (containerElement) {
                containerElement.textContent = containerType || 'Not selected';
            }
            
            // Get uploaded file
            const fileInput = document.getElementById('file_input');
            const fileElement = document.getElementById('reviewFileName');
            if (fileElement) {
                if (fileInput && fileInput.files && fileInput.files.length > 0) {
                    fileElement.textContent = fileInput.files[0].name;
                } else {
                    fileElement.textContent = 'No file uploaded';
                }
            }
            
            // Get route temperature
            const tempSlider = document.getElementById('temp_slider');
            const tempElement = document.getElementById('reviewRouteTemperature');
            if (tempElement) {
                if (tempSlider && tempSlider.value) {
                    tempElement.textContent = `${tempSlider.value}°C`;
                } else {
                    tempElement.textContent = 'Not specified';
                }
            }
            
            // Get optimization algorithm
            const algorithm = getSelectedAlgorithm();
            const algorithmElement = document.getElementById('reviewOptimizationAlgorithm');
            if (algorithmElement) {
                if (algorithm) {
                    let algorithmText = algorithm === 'genetic' ? 'AI-Enhanced Genetic' : 'Regular Packing';
                    
                    // Add genetic algorithm parameters if applicable
                    if (algorithm === 'genetic') {
                        const populationInput = document.getElementById('population_size');
                        const generationsInput = document.getElementById('num_generations');
                        
                        if (populationInput && generationsInput) {
                            const population = populationInput.value || '10';
                            const generations = generationsInput.value || '8';
                            algorithmText += ` (Population: ${population}, Generations: ${generations})`;
                        }
                    }
                    
                    algorithmElement.textContent = algorithmText;
                } else {
                    algorithmElement.textContent = 'Not selected';
                }
            }
            
            console.log('Review summary updated successfully');
        } catch (error) {
            console.error('Error updating review summary:', error);
        }
    }    // Helper function to get selected algorithm
    function getSelectedAlgorithm() {
        const algorithmInputs = document.querySelectorAll('input[name="optimization_mode"]');
        for (let input of algorithmInputs) {
            if (input.checked) {
                return input.value;
            }
        }
        
        // Fallback to hidden input if radio buttons aren't found
        const hiddenInput = document.getElementById('optimization_algorithm');
        return hiddenInput ? hiddenInput.value : null;
    }

  function goToStep(stepIndex) {
    console.log("========== goToStep called ==========");
    console.log("Going to step:", stepIndex);
    console.log("Available sections:", sections.length);
    console.log("Available steps:", steps.length);
    
    if (!sections || sections.length === 0) {
      console.error("No form sections found!");
      return;
    }
    
    // Debug current state
    sections.forEach((section, index) => {
      console.log(`Section ${index + 1} (${section.id}):`, section.classList.contains('active') ? 'ACTIVE' : 'inactive');
    });
    
    console.log("Removing active classes from all sections and steps...");
    sections.forEach(section => section.classList.remove('active'));
    steps.forEach(step => step.classList.remove('active'));
    
    if (sections[stepIndex - 1]) {
      console.log(`Activating section ${stepIndex}: ${sections[stepIndex - 1].id}`);
      sections[stepIndex - 1].classList.add('active');
    } else {
      console.error(`Section ${stepIndex} not found!`);
      return;
    }
    
    // Update step indicators
    for (let i = 0; i < stepIndex; i++) {
      if (steps[i]) steps[i].classList.add('active');
    }
    
    updateStepNavigation();
    updateReviewSummary();
  }

  function validateCurrentStep(stepNum) {
    switch(stepNum) {
      case 1:
        // Validate transport mode and container selection
        if (!transportMode || !transportMode.value) {
          showError('Please select a transport mode');
          return false;
        }
        
        if (transportMode.value !== '5' && (!containerType || !containerType.value)) {
          showError('Please select a container type');
          return false;
        }
        
        if (transportMode.value === '5') {
          const length = document.getElementById('length');
          const width = document.getElementById('width');
          const height = document.getElementById('height');
          
          if (!length || !length.value || !width || !width.value || !height || !height.value) {
            showError('Please enter all custom container dimensions');
            return false;
          }
        }
        return true;
        
      case 2:
        // Validate file upload
        if (!fileInput || !fileInput.files || !fileInput.files[0]) {
          showError('Please upload an inventory file');
          return false;
        }
        return true;
        
      case 3:
        // Settings validation (temperature is optional)
        return true;
        
      default:
        return true;
    }
  }

  // 4. ALGORITHM SELECTION FUNCTIONALITY
  const algorithmOptions = document.querySelectorAll('.algorithm-option');
  const optimizationAlgorithmInput = document.getElementById('optimization_algorithm');
  const geneticControls = document.querySelector('.genetic-controls');

  if (algorithmOptions.length > 0) {
    console.log("Found algorithm options:", algorithmOptions.length);

    algorithmOptions.forEach(option => {
      option.addEventListener('click', function() {
        console.log("Algorithm option clicked:", this.dataset.algorithm);
        
        // Remove selected class from all options
        algorithmOptions.forEach(opt => {
          opt.classList.remove('selected');
        });
        
        // Add selected class to clicked option
        this.classList.add('selected');
        
        // Update hidden input
        const algorithmValue = this.getAttribute('data-algorithm');
        if (optimizationAlgorithmInput) {
          optimizationAlgorithmInput.value = algorithmValue;
          console.log("Algorithm input set to:", algorithmValue);
        }
        
        // Show/hide genetic controls
        if (geneticControls) {
          if (algorithmValue === 'genetic') {
            geneticControls.style.display = 'block';
            console.log("Showing genetic controls");
          } else {
            geneticControls.style.display = 'none';
            console.log("Hiding genetic controls");
          }
        }
      });
    });
  } else {
    console.warn("No algorithm options found in DOM");
  }

  // Initialize genetic algorithm parameter sliders
    function initializeGeneticSliders() {
        // Population size slider
        const populationSlider = document.getElementById('population_size');
        const populationValue = document.getElementById('population_size_value');
        
        if (populationSlider && populationValue) {
            populationSlider.addEventListener('input', function() {
                populationValue.textContent = this.value;
                console.log('Population size updated to:', this.value);
            });
            
            // Set initial value
            populationValue.textContent = populationSlider.value || '10';
        }
        
        // Number of generations slider
        const generationsSlider = document.getElementById('num_generations');
        const generationsValue = document.getElementById('num_generations_value');
        
        if (generationsSlider && generationsValue) {
            generationsSlider.addEventListener('input', function() {
                generationsValue.textContent = this.value;
                console.log('Number of generations updated to:', this.value);
            });
            
            // Set initial value
            generationsValue.textContent = generationsSlider.value || '8';
        }
        
        console.log('Genetic algorithm sliders initialized');
    }

    // Enhanced algorithm selection with proper genetic controls
    function initializeAlgorithmSelection() {
        const algorithmOptions = document.querySelectorAll('.algorithm-option');
        const optimizationAlgorithmInput = document.getElementById('optimization_algorithm');
        const geneticControls = document.querySelector('.genetic-controls');
        
        console.log('Initializing algorithm selection. Found options:', algorithmOptions.length);
        
        algorithmOptions.forEach(option => {
            option.addEventListener('click', function() {
                const algorithm = this.dataset.algorithm;
                console.log('Algorithm selected:', algorithm);
                
                // Remove selected class from all options
                algorithmOptions.forEach(opt => opt.classList.remove('selected'));
                
                // Add selected class to clicked option
                this.classList.add('selected');
                
                // Update hidden input
                if (optimizationAlgorithmInput) {
                    optimizationAlgorithmInput.value = algorithm;
                    console.log('Hidden input updated to:', algorithm);
                }
                
                // Update radio button
                const radioButton = this.querySelector('input[type="radio"]');
                if (radioButton) {
                    radioButton.checked = true;
                    console.log('Radio button checked for:', algorithm);
                }
                
                // Show/hide genetic controls
                if (geneticControls) {
                    if (algorithm === 'genetic') {
                        geneticControls.style.display = 'block';
                        console.log('Genetic controls shown');
                    } else {
                        geneticControls.style.display = 'none';
                        console.log('Genetic controls hidden');
                    }
                }
            });
        });
        
        // Set default selection (regular algorithm)
        const defaultOption = document.querySelector('.algorithm-option[data-algorithm="regular"]');
        if (defaultOption) {
            defaultOption.click();
            console.log('Default algorithm (regular) selected');
        }
    }

  // 5. NAVIGATION EVENT LISTENERS
  if (nextBtn) {
    console.log("Setting up Next button event listener");
    nextBtn.addEventListener('click', function(e) {
      e.preventDefault();
      console.log("Next button clicked");
      
      const currentStepNum = Array.from(sections).findIndex(section => 
        section.classList.contains('active')) + 1;
      console.log("Current step number:", currentStepNum);
      
      // Validate current step before proceeding
      if (!validateCurrentStep(currentStepNum)) {
        console.log("Validation failed for step:", currentStepNum);
        return false;
      }
      
      console.log("Validation passed, proceeding to next step");
      if (currentStepNum < 4) {
        goToStep(currentStepNum + 1);
      } else {
        // Submit the form from the final step
        console.log("Final step reached, submitting form");
        if (optimizerForm) optimizerForm.submit();
      }
    });
  } else {
    console.error("Next button not found!");
  }

  if (prevBtn) {
    console.log("Setting up Previous button event listener");
    prevBtn.addEventListener('click', function(e) {
      e.preventDefault();
      console.log("Previous button clicked");
      
      const currentStepNum = Array.from(sections).findIndex(section => 
        section.classList.contains('active')) + 1;
      console.log("Going back from step:", currentStepNum);
      
      if (currentStepNum > 1) {
        goToStep(currentStepNum - 1);
      }
    });
  } else {
    console.error("Previous button not found!");
  }

  function showError(message) {
    console.error(message);
    
    const notification = document.createElement('div');
    notification.className = 'error-notification';
    notification.innerHTML = `
      <div class="error-icon"><i class="fas fa-exclamation-circle"></i></div>
      <div class="error-message">${message}</div>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
      notification.classList.add('visible');
    }, 10);
    
    setTimeout(() => {
      notification.classList.remove('visible');
      setTimeout(() => {
        document.body.removeChild(notification);
      }, 300);
    }, 3000);
  }

  // Initialize first step on page load
  goToStep(1);
  updateStepNavigation();
  initializeGeneticSliders();
  initializeAlgorithmSelection();
  initializeFormSubmission();
  
    // Form submission handler with enhanced validation
    function initializeFormSubmission() {
        const form = document.getElementById('optimizationForm');
        
        if (form) {
            form.addEventListener('submit', function(e) {
                console.log('Form submission initiated');
                
                // Validate all required fields
                const transportMode = getSelectedTransportMode();
                const fileInput = document.getElementById('file_input');
                const algorithm = getSelectedAlgorithm();
                
                if (!transportMode) {
                    e.preventDefault();
                    showError('Please select a transport mode');
                    goToStep(1);
                    return false;
                }
                
                if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
                    e.preventDefault();
                    showError('Please upload a data file');
                    goToStep(2);
                    return false;
                }
                
                if (!algorithm) {
                    e.preventDefault();
                    showError('Please select an optimization algorithm');
                    goToStep(4);
                    return false;
                }
                
                // If genetic algorithm is selected, ensure parameters are set
                if (algorithm === 'genetic') {
                    const populationSize = document.getElementById('population_size');
                    const numGenerations = document.getElementById('num_generations');
                    
                    if (populationSize && numGenerations) {
                        console.log('Genetic algorithm parameters:', {
                            population: populationSize.value,
                            generations: numGenerations.value
                        });
                    }
                }
                
                console.log('Form validation passed, submitting with algorithm:', algorithm);
                
                // Show loading overlay
                const loadingOverlay = document.getElementById('loadingOverlay');
                if (loadingOverlay) {
                    loadingOverlay.style.display = 'flex';
                }
                
                return true; // Allow form submission
            });
            
            console.log('Form submission handler initialized');
        } else {
            console.error('Optimization form not found');
        }
    }
});
