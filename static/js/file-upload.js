document.addEventListener("DOMContentLoaded", function () {
  const dropZone = document.getElementById("dropZone");
  const fileInput = dropZone.querySelector('input[type="file"]');
  const progressBar = dropZone.querySelector(".upload-progress");
  const progressIndicator = progressBar.querySelector(".progress-bar");
  const fileStatus = dropZone.querySelector(".file-status");
  const fileNameElement = document.getElementById("fileName");
  const csvPreview = document.getElementById("csvPreview");

  // Make the entire dropzone clickable
  dropZone.addEventListener("click", function (e) {
    if (e.target !== fileInput && !e.target.closest(".template-links")) {
      fileInput.click();
    }
  });

  // Handle file selection
  fileInput.addEventListener("change", function () {
    if (this.files.length > 0) {
      const file = this.files[0];
      const validTypes = [".csv", ".xlsx", ".xls"];
      const fileExt = file.name
        .substring(file.name.lastIndexOf("."))
        .toLowerCase();

      if (!validTypes.includes(fileExt)) {
        showError("Please select a CSV or Excel file");
        this.value = "";
        return;
      }

      // Show file name and progress
      fileNameElement.textContent = file.name;
      fileStatus.classList.add("active");
      progressBar.classList.add("active");

      // Simulate progress for demo
      let progress = 0;
      const interval = setInterval(() => {
        progress += 5;
        progressIndicator.style.width = `${progress}%`;
        if (progress >= 100) {
          clearInterval(interval);
          setTimeout(() => {
            // PreviewFile
            previewFile(file);
          }, 300);
        }
      }, 50);
    } else {
      resetUpload();
    }
  });

  // Drag and drop functionality
  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, highlight, false);
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, unhighlight, false);
  });

  // Prevent default drag behaviors
  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, preventDefaults, false);
  });

  // Handle dropped files
  dropZone.addEventListener("drop", handleDrop, false);

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

    if (files.length > 0) {
      fileInput.files = files;
      fileInput.dispatchEvent(new Event("change"));
    }
  }

  function resetUpload() {
    progressBar.classList.remove("active");
    fileStatus.classList.remove("active");
    progressIndicator.style.width = "0%";
    csvPreview.classList.add("d-none");
  }

  function showError(message) {
    // Create or update error message
    let errorEl = dropZone.querySelector(".upload-error");

    if (!errorEl) {
      errorEl = document.createElement("div");
      errorEl.className = "alert alert-danger mt-3 upload-error";
      dropZone.appendChild(errorEl);
    }

    errorEl.textContent = message;

    // Auto hide after 3 seconds
    setTimeout(() => {
      errorEl.remove();
    }, 3000);
  }

  function previewFile(file) {
    // Create FormData
    const formData = new FormData();
    formData.append("file", file);

    // Send AJAX request to preview endpoint
    fetch("/preview_csv", {
      method: "POST",
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          // Show preview
          const headers = document.getElementById("csvHeader");
          const tableBody = document.getElementById("csvData");

          // Create header row
          let headerHTML = "<tr>";
          data.columns.forEach((column) => {
            headerHTML += `<th>${column}</th>`;
          });
          headerHTML += "</tr>";
          headers.innerHTML = headerHTML;

          // Create data rows
          let bodyHTML = "";
          data.preview.forEach((row) => {
            bodyHTML += "<tr>";
            data.columns.forEach((column) => {
              bodyHTML += `<td>${row[column] !== null ? row[column] : ""}</td>`;
            });
            bodyHTML += "</tr>";
          });
          tableBody.innerHTML = bodyHTML;

          // Show the preview section with animation
          csvPreview.classList.remove("d-none");
          csvPreview.style.opacity = 0;
          setTimeout(() => {
            csvPreview.style.transition = "opacity 0.5s ease";
            csvPreview.style.opacity = 1;
          }, 10);
        } else {
          showError(data.error || "Error previewing file");
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        showError("Error processing the file. Please try again.");
      });
  }
});
