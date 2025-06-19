let currentStep = 1;
let csvData = null;

// Transport mode mapping
const transportModeMapping = {
  "1": "Truck",
  "2": "Ship", 
  "3": "Plane",
  "4": "Train",
  "5": "Custom"
};

function navigateStep(direction) {
  const newStep = currentStep + direction;
  if (newStep < 1 || newStep > 4) return;

  if (!validateStep(currentStep)) return;

  // Hide current step
  const currentSection = document.querySelector(`[data-step="${currentStep}"]`);
  if (currentSection) {
    currentSection.classList.remove("active");
  }

  // Show new step
  const newSection = document.querySelector(`[data-step="${newStep}"]`);
  if (newSection) {
    newSection.classList.add("active");
  }

  // Update step indicators
  document.querySelectorAll(".step").forEach((step, index) => {
    step.classList.toggle("active", index + 1 <= newStep);
  });

  currentStep = newStep;
  updateNavigationButtons();

  if (currentStep === 4) {
    updateReviewPage();
  }
}

function updateReviewPage() {
  // Update transport mode
  const transportSelect = document.getElementById("transport_mode");
  const reviewTransportMode = document.getElementById("reviewTransportMode");
  if (transportSelect && reviewTransportMode) {
    const selectedTransport = document.querySelector('.transport-option.selected');
    reviewTransportMode.textContent = selectedTransport ? 
      selectedTransport.querySelector('.option-title').textContent : "Not selected";
  }

  // Update container type
  const containerTypeInput = document.getElementById("container_type");
  const reviewContainerType = document.getElementById("reviewContainerType");
  if (reviewContainerType) {
    reviewContainerType.textContent = containerTypeInput ? containerTypeInput.value : "Not selected";
  }

  // Update route temperature
  const routeTemp = document.getElementById("route_temperature");
  const reviewRouteTemperature = document.getElementById("reviewRouteTemperature");
  if (reviewRouteTemperature) {
    reviewRouteTemperature.textContent = routeTemp && routeTemp.value
      ? `${routeTemp.value}°C`
      : "Not specified";
  }

  // Update file info
  const reviewFileName = document.getElementById("reviewFileName");
  if (reviewFileName) {
    const fileInput = document.getElementById("file_input");
    reviewFileName.textContent = fileInput && fileInput.files && fileInput.files[0] 
      ? fileInput.files[0].name 
      : "No file uploaded";
  }

  // Update CSV summary if available
  if (csvData) {
    const reviewTotalItems = document.getElementById("reviewTotalItems");
    const reviewTotalWeight = document.getElementById("reviewTotalWeight");
    
    if (reviewTotalItems) {
      reviewTotalItems.textContent = csvData.length;
    }
    
    if (reviewTotalWeight) {
      const totalWeight = csvData.reduce(
        (sum, row) => sum + (parseFloat(row.Weight) || 0),
        0
      );
      reviewTotalWeight.textContent = totalWeight.toFixed(2) + " kg";
    }
  }
}

function validateStep(step) {
  switch (step) {
    case 1:
      // Validate transport mode and container selection
      const transportMode = document.getElementById("transport_mode");
      const containerType = document.getElementById("container_type");

      if (!transportMode || !transportMode.value) {
        alert("Please select a transport mode");
        return false;
      }
      
      if (transportMode.value !== "5" && (!containerType || !containerType.value)) {
        alert("Please select a container type");
        return false;
      }
      
      if (transportMode.value === "5") {
        const length = document.getElementById("length");
        const width = document.getElementById("width");
        const height = document.getElementById("height");
        
        if (!length || !length.value || !width || !width.value || !height || !height.value) {
          alert("Please enter all custom dimensions");
          return false;
        }
      }
      return true;

    case 2:
      // Validate file upload
      const fileInput = document.getElementById("file_input");
      if (!fileInput || !fileInput.files || !fileInput.files[0]) {
        alert("Please upload a file");
        return false;
      }
      return true;

    case 3:
      // Settings are optional
      return true;

    default:
      return true;
  }
}

function updateNavigationButtons() {
  const prevBtn = document.getElementById("prev1");
  const nextBtn = document.getElementById("next1");

  if (prevBtn) {
    prevBtn.style.display = currentStep === 1 ? "none" : "block";
  }
  
  if (nextBtn) {
    if (currentStep === 4) {
      nextBtn.innerHTML = '<i class="fas fa-rocket"></i> Optimize';
      nextBtn.type = "submit";
    } else {
      nextBtn.innerHTML = 'Next <i class="fas fa-arrow-right"></i>';
      nextBtn.type = "button";
    }
  }
}

function submitForm() {
  const form = document.getElementById("optimizerForm");
  if (form) {
    form.submit();
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
  updateNavigationButtons();
});
