/**
 * Main application logic for the GravitycARgo cargo input interface
 */
document.addEventListener("DOMContentLoaded", function () {
  // Initialize TableManager
  const tableManager = new TableManager(
    "cargoTable",
    CONFIG.TABLE_COLUMNS,
    CONFIG.DEFAULT_ROW
  );
  tableManager.initialize();

  // Check for saved data
  if (tableManager.loadFromLocalStorage()) {
    // Show session restore modal
    const sessionModal = new bootstrap.Modal(
      document.getElementById("sessionRestoreModal")
    );
    sessionModal.show();

    // Handle restore button
    document
      .getElementById("restoreSessionButton")
      .addEventListener("click", function () {
        sessionModal.hide();
        Swal.fire({
          title: "Session Restored",
          text: "Your previous cargo data has been loaded.",
          icon: "success",
          timer: 2000,
          showConfirmButton: false,
        });
      });

    // Handle Start Fresh button
    document
      .querySelector("#sessionRestoreModal .btn-secondary")
      .addEventListener("click", function () {
        tableManager.clearData();
        sessionModal.hide();
        Swal.fire({
          title: "Fresh Start",
          text: "Starting with a clean cargo table.",
          icon: "success",
          timer: 2000,
          showConfirmButton: false,
        });
      });
  }

  // Handle Save Draft button
  document.getElementById("saveButton").addEventListener("click", function () {
    tableManager.saveToLocalStorage();
    Swal.fire({
      title: "Saved",
      text: "Your cargo data has been saved locally.",
      icon: "success",
      timer: 2000,
      showConfirmButton: false,
    });
  });

  // Handle Clear All button
  document
    .getElementById("clearAllButton")
    .addEventListener("click", function () {
      Swal.fire({
        title: "Clear All Data?",
        text: "Are you sure you want to clear all cargo data? This cannot be undone.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: "Yes, clear it!",
        cancelButtonText: "Cancel",
      }).then((result) => {
        if (result.isConfirmed) {
          tableManager.clearData();
          Swal.fire({
            title: "Cleared",
            text: "All cargo data has been cleared.",
            icon: "success",
            timer: 2000,
            showConfirmButton: false,
          });
        }
      });
    });

  // Handle Add Row button
  document
    .getElementById("addRowButton")
    .addEventListener("click", function () {
      tableManager.addRow();
    });

  // Handle Remove Selected button
  document
    .getElementById("removeRowButton")
    .addEventListener("click", function () {
      tableManager.removeSelectedRows();
    });

  // Handle Undo button
  document.getElementById("undoButton").addEventListener("click", function () {
    tableManager.undo();
  });

  // Handle Redo button
  document.getElementById("redoButton").addEventListener("click", function () {
    tableManager.redo();
  });

  // Handle AI Fill button
  document
    .getElementById("aiFillButton")
    .addEventListener("click", function () {
      tableManager.showAiFillModal();
    });

  // Handle Upload button
  document
    .getElementById("uploadButton")
    .addEventListener("click", function () {
      document.getElementById("fileInput").click();
    });

  // Handle file selection
  document
    .getElementById("fileInput")
    .addEventListener("change", async function (e) {
      if (!e.target.files || e.target.files.length === 0) return;

      const file = e.target.files[0];

      // Show loading
      Swal.fire({
        title: "Processing File",
        html: "Please wait while we process your file...",
        allowOutsideClick: false,
        didOpen: () => {
          Swal.showLoading();
        },
      });

      try {
        // Import the file
        const importedData = await exportService.importFromFile(file);

        // Update table with imported data
        tableManager.setDataFromFile(importedData);

        // Show success message
        Swal.fire({
          title: "Import Successful",
          text: `Imported ${importedData.length} cargo items.`,
          icon: "success",
        });
      } catch (error) {
        console.error("Error importing file:", error);
        Swal.fire({
          title: "Import Failed",
          text: "Could not process the file. Please check the format and try again.",
          icon: "error",
        });
      }

      // Reset file input
      e.target.value = "";
    });

  // Handle Export to Excel
  document.getElementById("exportExcel").addEventListener("click", function () {
    const data = tableManager.getData();
    const validationStatus = tableManager.getValidationStatus();
    exportService.exportToExcel(data, validationStatus);
  });

  // Handle Export to CSV
  document.getElementById("exportCSV").addEventListener("click", function () {
    const data = tableManager.getData();
    const validationStatus = tableManager.getValidationStatus();
    exportService.exportToCSV(data, validationStatus);
  });

  // Handle Continue to Optimization button
  document
    .getElementById("continueButton")
    .addEventListener("click", function () {
      const data = tableManager.getData();
      const validationStatus = tableManager.getValidationStatus();

      // First check for validation issues
      if (validationStatus && validationStatus.hasIssues) {
        Swal.fire({
          title: "Validation Issues Found",
          html: `
            <div class="validation-warning">
              <p class="mb-2">Your cargo data has ${
                validationStatus.totalIssues
              } validation ${
            validationStatus.totalIssues === 1 ? "issue" : "issues"
          } in ${validationStatus.itemsAffected} ${
            validationStatus.itemsAffected === 1 ? "item" : "items"
          }.</p>
              
              <div class="alert alert-warning">
                <ul class="mb-0 text-start">
                  ${validationStatus.issues
                    .slice(0, 5) // Show max 5 issues
                    .map(
                      (issue) =>
                        `<li><strong>${issue.itemName}</strong>: ${issue.message} (${issue.field})</li>`
                    )
                    .join("")}
                  ${
                    validationStatus.issues.length > 5
                      ? `<li>...and ${
                          validationStatus.issues.length - 5
                        } more issues</li>`
                      : ""
                  }
                </ul>
              </div>
              
              <p>Do you want to proceed anyway?</p>
            </div>
          `,
          icon: "warning",
          showCancelButton: true,
          confirmButtonText: "Continue to Optimization anyway",
          cancelButtonText: "Go back and fix issues",
        }).then((result) => {
          if (result.isConfirmed) {
            // Continue to optimization page despite warnings
            window.location.href = "../optimization/index.html";
          }
        });
        return;
      }

      // Check if export is needed (no validation issues)
      if (exportService.isExportNeeded(data)) {
        Swal.fire({
          title: "Export Recommended",
          text: "You have not exported your data recently. Would you like to export it now?",
          icon: "question",
          showCancelButton: true,
          confirmButtonText: "Yes, export",
          cancelButtonText: "Continue without exporting",
        }).then((result) => {
          if (result.isConfirmed) {
            // Export to Excel
            const exported = exportService.exportToExcel(data);

            if (exported) {
              // Redirect to optimization page
              setTimeout(() => {
                window.location.href = "../optimization/index.html";
              }, 1000);
            }
          } else {
            // Redirect to optimization page
            window.location.href = "../optimization/index.html";
          }
        });
      } else {
        // No export needed, redirect to optimization page
        window.location.href = "../optimization/index.html";
      }
    });

  // Review tab activation
  document.getElementById("review-tab").addEventListener("click", function () {
    // Create preview table when tab is selected
    tableManager.createPreviewTable("previewTable");

    // Update data statistics
    const data = tableManager.getData();
    tableManager.updateDataStats(data);
  });

  // Theme switcher
  document
    .getElementById("themeSwitcher")
    .addEventListener("click", function () {
      document.body.classList.toggle("dark-mode");

      // Update button
      const themeButton = this;
      const icon = themeButton.querySelector("i");

      if (document.body.classList.contains("dark-mode")) {
        icon.classList.remove("fa-moon");
        icon.classList.add("fa-sun");
        themeButton.innerHTML = icon.outerHTML + " Light Mode";
        localStorage.setItem(CONFIG.STORAGE_KEYS.THEME, "dark");
      } else {
        icon.classList.remove("fa-sun");
        icon.classList.add("fa-moon");
        themeButton.innerHTML = icon.outerHTML + " Dark Mode";
        localStorage.setItem(CONFIG.STORAGE_KEYS.THEME, "light");
      }
    });

  // Initialize theme from localStorage
  const savedTheme = localStorage.getItem(CONFIG.STORAGE_KEYS.THEME);
  if (savedTheme === "dark") {
    document.getElementById("themeSwitcher").click();
  }
  // Network connection monitoring
  window.addEventListener("offline", function () {
    Swal.fire({
      title: "Network Connection Lost",
      text: "You are currently offline. Some features like AI suggestions may not work.",
      icon: "warning",
      toast: true,
      position: "top-end",

      showConfirmButton: false,
      timer: 3000,
    });
  });
});
