// Add these variables at the top of your file
const transportModeMapping = {
  "1": "Truck",
  "2": "Ship",
  "3": "Plane",
  "4": "Train",
  "5": "Custom"
};

document.addEventListener("DOMContentLoaded", function () {
  console.log("Main.js loaded successfully");

  // Transport mode selection - COMPLETELY FIXED
  const transportOptions = document.querySelectorAll(".transport-option");
  const transportModeInput = document.getElementById("transport_mode");

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
        if (transportModeInput) {
          transportModeInput.value = transportValue;
          console.log("Transport mode input set to:", transportValue);
        }

        // Enable next button
        const nextBtn = document.getElementById("next1");
        if (nextBtn) {
          nextBtn.disabled = false;
          nextBtn.classList.remove("disabled"); // Assuming 'disabled' class controls appearance
        }

        // Handle container options display
        updateContainerDisplay(transportValue);
      });
    });
  } else {
    console.error("No transport options found in DOM");
  }

  function updateContainerDisplay(transportMode) {
    console.log("Updating container display for mode:", transportMode);

    const containerOptions = document.getElementById("container_options");
    const customDimensions = document.getElementById("custom_dimensions");

    if (!containerOptions || !customDimensions) {
      console.error("Container display elements not found");
      return;
    }

    if (transportMode === "5") {
      // Custom container
      customDimensions.style.display = "block";
      containerOptions.style.display = "none";
      console.log("Showing custom dimensions form");
    } else {
      // Predefined containers
      customDimensions.style.display = "none";
      containerOptions.style.display = "block";
      loadContainerOptions();
    }
  }

  function loadContainerOptions() {
    const transportMode = document.getElementById("transport_mode").value;
    console.log("Loading container options for transport mode:", transportMode);

    // Check if defaultData is available from the global scope
    if (typeof defaultData === 'undefined' || !defaultData.transport_modes) {
      console.error("Transport modes data not available");
      return;
    }

    // Find the transport mode data
    const transportModeData = defaultData.transport_modes.find(mode => mode.id === transportMode);
    
    if (!transportModeData) {
      console.error("Transport mode data not found for ID:", transportMode);
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
        <div class="container-volume">${container.volume.toFixed(1)} m³</div>
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
        
        const containerTypeInput = document.getElementById("container_type");
        if (containerTypeInput) {
          containerTypeInput.value = container.name;
        }
        console.log("Container selected:", container.name, "for transport mode:", transportMode);
      });

      containerGrid.appendChild(containerCard);
    });

    console.log("Added", transportModeData.containers.length, "container options");
  }

  // File input validation
  const fileInput = document.querySelector('input[type="file"]');
  if (fileInput) {
    fileInput.addEventListener("change", function () {
      if (this.files.length > 0) {
        const fileName = this.files[0].name;
        if (
          !fileName.endsWith(".csv") &&
          !fileName.endsWith(".xlsx") &&
          !fileName.endsWith(".xls")
        ) {
          alert("Please upload a CSV or Excel file");
          this.value = "";
        }
      }
    });
  }

  // Enhanced file upload handling
  const dropZone = document.querySelector(".file-upload-container");
  if (dropZone) {
    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, preventDefaults);
    });

    ["dragenter", "dragover"].forEach((eventName) => {
      dropZone.addEventListener(eventName, highlight);
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, unhighlight);
    });

    dropZone.addEventListener("drop", handleDrop);

    function preventDefaults(e) {
      e.preventDefault();
      e.stopPropagation();
    }

    function highlight() {
      dropZone.classList.add("drag-over");
    }

    function unhighlight() {
      dropZone.classList.remove("drag-over");
    }

    function handleDrop(e) {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (fileInput) {
        fileInput.files = files;
        handleFileSelect();
      }
    }

    function handleFileSelect() {
      if (fileInput && fileInput.files.length > 0) {
        const file = fileInput.files[0];
        showToast("File selected: " + file.name, "success");
        validateAndPreviewFile(file);
      }
    }
  }

  // Enhanced visualization controls
  document.querySelectorAll(".control-button").forEach((button) => {
    button.addEventListener("mouseover", () => {
      const tooltip = button.getAttribute("data-tooltip");
      if (tooltip) {
        showTooltip(button, tooltip);
      }
    });
  });

  function showTooltip(element, text) {
    const tooltip = document.createElement("div");
    tooltip.className = "tooltip";
    tooltip.textContent = text;
    document.body.appendChild(tooltip);

    const rect = element.getBoundingClientRect();
    tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + "px";
    tooltip.style.left =
      rect.left + (rect.width - tooltip.offsetWidth) / 2 + "px";

    element.addEventListener("mouseleave", () => tooltip.remove());
  }

  // Loading indicator
  function showLoading() {
    const loading = document.createElement("div");
    loading.className = "loading-overlay";
    loading.innerHTML = `
      <div class="loading-content">
        <div class="loading-spinner"></div>
        <p>Optimizing container packing...</p>
      </div>
    `;
    document.body.appendChild(loading);
  }

  // Initialize all constraint sliders
  function initializeConstraintSliders() {
    const sliders = {
      'volume_weight': 'volume_weight_value',
      'stability_weight': 'stability_weight_value',
      'contact_weight': 'contact_weight_value',
      'balance_weight': 'balance_weight_value',
      'items_packed_weight': 'items_packed_weight_value',
      'temperature_weight': 'temperature_weight_value',
      'weight_capacity': 'weight_capacity_value',
      'population_size': 'population_size_value',
      'num_generations': 'num_generations_value'
    };

    Object.entries(sliders).forEach(([sliderId, valueId]) => {
      const slider = document.getElementById(sliderId);
      const valueDisplay = document.getElementById(valueId);
      
      if (slider && valueDisplay) {
        // Set initial value
        valueDisplay.textContent = slider.value + (sliderId.includes('weight') ? '%' : '');
        
        // Add event listener
        slider.addEventListener('input', function() {
          valueDisplay.textContent = this.value + (sliderId.includes('weight') ? '%' : '');
        });
      }
    });
  }

  // Initialize constraint presets
  function initializeConstraintPresets() {
    const presets = {
      'balanced': {
        volume_weight: 50,
        stability_weight: 50,
        contact_weight: 50,
        balance_weight: 50,
        items_packed_weight: 50,
        temperature_weight: 50,
        weight_capacity: 50
      },
      'volume': {
        volume_weight: 80,
        stability_weight: 30,
        contact_weight: 40,
        balance_weight: 30,
        items_packed_weight: 70,
        temperature_weight: 30,
        weight_capacity: 40
      },
      'stability': {
        volume_weight: 30,
        stability_weight: 80,
        contact_weight: 70,
        balance_weight: 70,
        items_packed_weight: 30,
        temperature_weight: 40,
        weight_capacity: 60
      }
    };

    document.querySelectorAll('.constraint-preset').forEach(button => {
      button.addEventListener('click', function() {
        const preset = presets[this.dataset.preset];
        if (preset) {
          Object.entries(preset).forEach(([sliderId, value]) => {
            const slider = document.getElementById(sliderId);
            const valueDisplay = document.getElementById(sliderId + '_value');
            if (slider && valueDisplay) {
              slider.value = value;
              valueDisplay.textContent = value + '%';
            }
          });
        }
      });
    });
  }

  // Initialize all UI components when the page loads
  document.addEventListener('DOMContentLoaded', function() {
    initializeConstraintSliders();
    initializeConstraintPresets();
    initializeAlgorithmSelection();
  });

  // Initialize algorithm selection
  function initializeAlgorithmSelection() {
    const algorithmOptions = document.querySelectorAll('.algorithm-option');
    const algorithmInput = document.getElementById('optimization_algorithm');
    const geneticControls = document.querySelector('.genetic-controls');

    if (algorithmOptions.length > 0) {
      algorithmOptions.forEach(option => {
        option.addEventListener('click', function() {
          // Remove selected class from all options
          algorithmOptions.forEach(opt => {
            opt.classList.remove('selected');
            opt.classList.remove('active');
          });

          // Add selected class to clicked option
          this.classList.add('selected');
          this.classList.add('active');

          // Update hidden input value
          const selectedAlgorithm = this.dataset.algorithm;
          if (algorithmInput) {
            algorithmInput.value = selectedAlgorithm;
          }

          // Show/hide genetic algorithm controls
          if (geneticControls) {
            geneticControls.style.display = selectedAlgorithm === 'genetic' ? 'block' : 'none';
          }

          // Update sliders visibility
          const weightCapacitySlider = document.querySelector('.constraint-slider-item:has(#weight_capacity)');
          if (weightCapacitySlider) {
            weightCapacitySlider.style.display = selectedAlgorithm === 'genetic' ? 'block' : 'none';
          }
        });
      });

      // Set initial state
      const initialAlgorithm = algorithmInput ? algorithmInput.value : 'regular';
      const initialOption = document.querySelector(`.algorithm-option[data-algorithm="${initialAlgorithm}"]`);
      if (initialOption) {
        initialOption.classList.add('selected');
        initialOption.classList.add('active');
      }
      if (geneticControls) {
        geneticControls.style.display = initialAlgorithm === 'genetic' ? 'block' : 'none';
      }
    }
  }

  function hideLoading() {
    const loading = document.querySelector(".loading-overlay");
    if (loading) {
      loading.remove();
    }
  }

  // Error handling
  function showError(message) {
    const alert = document.createElement("div");
    alert.className = "alert alert-danger alert-dismissible fade show";
    alert.innerHTML = `
          <strong>Error!</strong> ${message}
          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      `;
    document
      .querySelector(".container")
      .insertBefore(alert, document.querySelector(".card"));
  }

  // Toast notifications
  function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas fa-${
          type === "success" ? "check-circle" : "info-circle"
        }"></i>
        <span>${message}</span>
    `;

    const container =
      document.querySelector(".toast-container") || createToastContainer();
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  function createToastContainer() {
    const container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
    return container;
  }

  // Additional utility functions
  function validateAndPreviewFile(file) {
    // File validation logic here
    console.log("Validating file:", file.name);
  }

  // WebSocket functionality
  function initializeWebSocket() {
    if (typeof WebSocket !== 'undefined') {
      const socket = new WebSocket('ws://localhost:8000/ws');
      
      socket.onmessage = function (event) {
        const data = JSON.parse(event.data);
        updateStats(data);
        updateVisualization(data);
      };
    }
  }

  function updateStats(data) {
    document.querySelectorAll(".stats-card").forEach((card) => {
      const key = card.getAttribute("data-stat");
      if (data[key]) {
        const value = card.querySelector(".stat-value");
        animateNumber(
          value,
          parseFloat(value.textContent),
          parseFloat(data[key])
        );
      }
    });
  }

  function animateNumber(element, start, end) {
    const duration = 1000;
    const steps = 60;
    const step = (end - start) / steps;
    let current = start;

    const animate = setInterval(() => {
      current += step;
      element.textContent = current.toFixed(1);

      if ((step > 0 && current >= end) || (step < 0 && current <= end)) {
        element.textContent = end.toFixed(1);
        clearInterval(animate);
      }
    }, duration / steps);
  }

  // Initialize WebSocket on page load
  document.addEventListener("DOMContentLoaded", function() {
    initializeWebSocket();
  });
});
