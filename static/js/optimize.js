let currentStep = 1;

let csvData = null;

function navigateStep(direction) {
  const newStep = currentStep + direction;
  if (newStep < 1 || newStep > 3) return;

  if (!validateStep(currentStep)) return;

  document.querySelector(`#step${currentStep}`).classList.remove("active");
  document.querySelector(`#step${newStep}`).classList.add("active");

  // Update step indicators
  document.querySelectorAll(".step-bubble").forEach((bubble, index) => {
    bubble.classList.toggle("active", index + 1 <= newStep);
  });

  currentStep = newStep;
  updateNavigationButtons();

  if (currentStep === 3) {
    updateReviewPage();
  }
}

function updateReviewPage() {
  // Update container details
  document.getElementById("reviewTransportMode").textContent =
    document.getElementById("transport_mode").options[
      document.getElementById("transport_mode").selectedIndex
    ].text;
  document.getElementById("reviewContainerType").textContent =
    document.getElementById("container_type").value;
  document.getElementById("reviewDimensions").textContent =
    document.getElementById("lengthValue").textContent +
    " × " +
    document.getElementById("widthValue").textContent +
    " × " +
    document.getElementById("heightValue").textContent;

  // Add route temperature to review
  const routeTemp = document.getElementById("route_temperature").value;
  document.getElementById("reviewRouteTemperature").textContent = routeTemp
    ? `${routeTemp}°C`
    : "Not specified";

  // Update CSV summary if available
  if (csvData) {
    document.getElementById("reviewTotalItems").textContent = csvData.length;
    const totalWeight = csvData.reduce(
      (sum, row) => sum + (parseFloat(row.Weight) || 0),
      0
    );
    document.getElementById("reviewTotalWeight").textContent =
      totalWeight.toFixed(2) + " kg";
  }
}

function validateStep(step) {
  switch (step) {
    case 1:
      // Validate container configuration
      const transportMode = document.getElementById("transport_mode").value;
      const containerType = document.getElementById("container_type").value;
      const routeTemp = document.getElementById("route_temperature").value;

      if (!transportMode) {
        alert("Please select a transport mode");
        return false;
      }
      if (transportMode !== "5" && !containerType) {
        alert("Please select a container type");
        return false;
      }
      // Route temperature is optional, so no validation needed
      return true;

    case 2:
      // Validate file upload
      if (!csvData) {
        alert("Please upload a file");
        return false;
      }
      return true;

    default:
      return true;
  }
}

function updateNavigationButtons() {
  const prevBtn = document.getElementById("prevBtn");
  const nextBtn = document.getElementById("nextBtn");

  prevBtn.style.display = currentStep === 1 ? "none" : "block";
  if (currentStep === 3) {
    nextBtn.textContent = "Submit";
    nextBtn.onclick = submitForm;
  } else {
    nextBtn.textContent = "Next";
    nextBtn.onclick = () => navigateStep(1);
  }
}

function submitForm() {
  const form = new FormData();

  // Add container configuration
  form.append(
    "transport_mode",
    document.getElementById("transport_mode").value
  );
  form.append(
    "container_type",
    document.getElementById("container_type").value
  );

  // Add route temperature if specified
  const routeTemp = document.getElementById("route_temperature").value;
  if (routeTemp) {
    form.append("route_temperature", routeTemp);
  }

  // Add file if available
  const fileInput = document.getElementById("csvFile");
  if (fileInput.files[0]) {
    form.append("file", fileInput.files[0]);
  }

  // Update UI to show loading state
  const nextBtn = document.getElementById("nextBtn");
  nextBtn.disabled = true;
  nextBtn.innerHTML =
    '<i class="fas fa-circle-notch fa-spin"></i> Processing...';

  // Submit the form
  fetch("/optimize", {
    method: "POST",
    body: form,
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error("Optimization failed");
      }
      return response.text();
    })
    .then((html) => {
      // Replace the current page content with the results
      document.documentElement.innerHTML = html;
    })
    .catch((error) => {
      alert("Error during optimization: " + error.message);
      nextBtn.disabled = false;
      nextBtn.innerHTML = "Submit";
    });
}
