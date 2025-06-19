/**
 * Container Visualization Module
 * Handles the 3D visualization of containers in the specifications section
 */

document.addEventListener("DOMContentLoaded", function () {
  // Get references to container visualization elements
  const containerModel = document.querySelector(".container-3d");

  if (!containerModel) return; // Exit if container model not found

  // Function to update the 3D container model with proper dimensions and positioning
  window.updateContainerModel = function (dimensions) {
    const [length, width, height] = dimensions;

    // Calculate scale factor to keep model within bounds
    const maxDim = Math.max(length, width, height);
    const scaleFactor = 100 / maxDim; // Base size adjusted for better visibility

    // Set CSS variables for dimensions - ensure they're properly sized
    containerModel.style.setProperty("--length", `${length * scaleFactor}px`);
    containerModel.style.setProperty("--width", `${width * scaleFactor}px`);
    containerModel.style.setProperty("--height", `${height * scaleFactor}px`);

    // Reset existing container faces to ensure clean slate
    const existingFaces = containerModel.querySelectorAll(".container-face");
    existingFaces.forEach((face) => face.remove());

    // Create fresh container faces with correct dimensions and positioning
    const faces = [
      { class: "front", backgroundColor: "rgba(59, 130, 246, 0.3)" },
      { class: "back", backgroundColor: "rgba(59, 130, 246, 0.15)" },
      { class: "right", backgroundColor: "rgba(99, 102, 241, 0.2)" },
      { class: "left", backgroundColor: "rgba(99, 102, 241, 0.2)" },
      { class: "top", backgroundColor: "rgba(139, 92, 246, 0.25)" },
      { class: "bottom", backgroundColor: "rgba(139, 92, 246, 0.15)" },
    ];

    faces.forEach((faceConfig) => {
      const face = document.createElement("div");
      face.className = `container-face ${faceConfig.class}`;
      face.style.backgroundColor = faceConfig.backgroundColor;
      containerModel.appendChild(face);
    });

    // Apply correct transforms to new faces
    const newFaces = containerModel.querySelectorAll(".container-face");
    newFaces.forEach((face) => {
      if (face.classList.contains("front")) {
        face.style.width = `var(--length)`;
        face.style.height = `var(--height)`;
        face.style.transform = `translateX(-50%) translateY(-50%) translateZ(calc(var(--width) / 2))`;
      } else if (face.classList.contains("back")) {
        face.style.width = `var(--length)`;
        face.style.height = `var(--height)`;
        face.style.transform = `translateX(-50%) translateY(-50%) translateZ(calc(var(--width) / -2))`;
      } else if (face.classList.contains("right")) {
        face.style.width = `var(--width)`;
        face.style.height = `var(--height)`;
        face.style.transform = `translateX(-50%) translateY(-50%) rotateY(90deg) translateZ(calc(var(--length) / 2))`;
      } else if (face.classList.contains("left")) {
        face.style.width = `var(--width)`;
        face.style.height = `var(--height)`;
        face.style.transform = `translateX(-50%) translateY(-50%) rotateY(-90deg) translateZ(calc(var(--length) / 2))`;
      } else if (face.classList.contains("top")) {
        face.style.width = `var(--length)`;
        face.style.height = `var(--width)`;
        face.style.transform = `translateX(-50%) translateY(-50%) rotateX(90deg) translateZ(calc(var(--height) / 2))`;
      } else if (face.classList.contains("bottom")) {
        face.style.width = `var(--length)`;
        face.style.height = `var(--width)`;
        face.style.transform = `translateX(-50%) translateY(-50%) rotateX(-90deg) translateZ(calc(var(--height) / 2))`;
      }
    });    // Update the specification values
    const lengthValue = document.querySelector("#lengthValue");
    const widthValue = document.querySelector("#widthValue");
    const heightValue = document.querySelector("#heightValue");
    const volumeValue = document.querySelector("#volumeValue");
    
    if (lengthValue) lengthValue.textContent = `${length}m`;
    if (widthValue) widthValue.textContent = `${width}m`;
    if (heightValue) heightValue.textContent = `${height}m`;
    if (volumeValue) volumeValue.textContent = `${(length * width * height).toFixed(2)} m³`;
  };

  // Add interactivity - make container rotate on hover/mouse movement
  containerModel.addEventListener("mousemove", function (e) {
    const containerRect = this.getBoundingClientRect();
    const mouseX = e.clientX - containerRect.left - containerRect.width / 2;
    const mouseY = e.clientY - containerRect.top - containerRect.height / 2;

    // Calculate rotation based on mouse position
    const rotateX = -mouseY * 0.1;
    const rotateY = mouseX * 0.1;

    // Apply rotation transformation
    this.style.transform = `rotateX(${30 + rotateX}deg) rotateY(${
      45 + rotateY
    }deg)`;
  });

  // Reset rotation when mouse leaves
  containerModel.addEventListener("mouseleave", function () {
    this.style.transform = "rotateX(30deg) rotateY(45deg)";
  });

  // Initialize with a default container size if needed
  const defaultDimensions = [12, 2.4, 2.6]; // Length, Width, Height
  if (containerModel) {
    updateContainerModel(defaultDimensions);
  }

  // Connect to container selection if it exists in the page
  const containerOptions = document.querySelectorAll(".container-option");

  containerOptions.forEach((option) => {
    option.addEventListener("click", function () {
      const containerName = this.dataset.value;
      const dimensionsText = this.querySelector(".container-dims")?.textContent;

      if (dimensionsText) {
        // Parse dimensions from the text (assuming format like "12m × 2.4m × 2.6m")
        const dimMatches = dimensionsText.match(/\d+(\.\d+)?/g);
        if (dimMatches && dimMatches.length >= 3) {
          const dimensions = [
            parseFloat(dimMatches[0]),
            parseFloat(dimMatches[1]),
            parseFloat(dimMatches[2]),
          ];
          updateContainerModel(dimensions);
        }
      }
    });
  });

  // Also connect to custom dimensions inputs if they exist
  const lengthInput = document.getElementById("length");
  const widthInput = document.getElementById("width");
  const heightInput = document.getElementById("height");

  if (lengthInput && widthInput && heightInput) {
    const updateFromInputs = () => {
      const length = parseFloat(lengthInput.value) || 0;
      const width = parseFloat(widthInput.value) || 0;
      const height = parseFloat(heightInput.value) || 0;

      if (length > 0 && width > 0 && height > 0) {
        updateContainerModel([length, width, height]);
      }
    };

    lengthInput.addEventListener("input", updateFromInputs);
    widthInput.addEventListener("input", updateFromInputs);
    heightInput.addEventListener("input", updateFromInputs);
  }
});
