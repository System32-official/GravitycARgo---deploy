/**
 * ExportService class for exporting data to different formats
 */
class ExportService {
  /**
   * Export data to Excel format with validation warning if needed
   * @param {Array} data - The data to export
   * @param {Object} validationStatus - Validation status from tableManager
   * @param {string} filename - The filename to use
   */
  exportToExcel(data, validationStatus, filename = "GravitycARgo-Cargo-Data") {
    if (!data || data.length === 0) {
      Swal.fire({
        title: "No Data",
        text: "There is no data to export",
        icon: "warning",
      });
      return;
    }

    // Show warning if there are validation issues
    if (validationStatus && validationStatus.hasIssues) {
      return this._showValidationWarning("Excel", validationStatus, () => {
        this._doExportToExcel(data, filename);
      });
    } else {
      return this._doExportToExcel(data, filename);
    }
  }

  /**
   * Actually perform the Excel export
   * @private
   */
  _doExportToExcel(data, filename) {
    try {
      // Create a workbook
      const wb = XLSX.utils.book_new();

      // Create a worksheet
      const ws = XLSX.utils.json_to_sheet(data);

      // Add the worksheet to the workbook
      XLSX.utils.book_append_sheet(wb, ws, "Cargo Items");

      // Save the workbook
      XLSX.writeFile(wb, `${filename}.xlsx`);

      // Update last export timestamp
      localStorage.setItem(
        CONFIG.STORAGE_KEYS.LAST_EXPORT,
        new Date().toISOString()
      );

      return true;
    } catch (error) {
      console.error("Error exporting to Excel:", error);
      Swal.fire({
        title: "Export Failed",
        text: "Failed to export data to Excel",
        icon: "error",
      });
      return false;
    }
  }

  /**
   * Export data to CSV format with validation warning if needed
   * @param {Array} data - The data to export
   * @param {Object} validationStatus - Validation status from tableManager
   * @param {string} filename - The filename to use
   */
  exportToCSV(data, validationStatus, filename = "GravitycARgo-Cargo-Data") {
    if (!data || data.length === 0) {
      Swal.fire({
        title: "No Data",
        text: "There is no data to export",
        icon: "warning",
      });
      return;
    }

    // Show warning if there are validation issues
    if (validationStatus && validationStatus.hasIssues) {
      return this._showValidationWarning("CSV", validationStatus, () => {
        this._doExportToCSV(data, filename);
      });
    } else {
      return this._doExportToCSV(data, filename);
    }
  }

  /**
   * Actually perform the CSV export
   * @private
   */
  _doExportToCSV(data, filename) {
    try {
      // Convert data to CSV
      const ws = XLSX.utils.json_to_sheet(data);
      const csv = XLSX.utils.sheet_to_csv(ws);

      // Create a download link
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${filename}.csv`);
      document.body.appendChild(link);

      // Trigger the download
      link.click();

      // Clean up
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      // Update last export timestamp
      localStorage.setItem(
        CONFIG.STORAGE_KEYS.LAST_EXPORT,
        new Date().toISOString()
      );

      return true;
    } catch (error) {
      console.error("Error exporting to CSV:", error);
      Swal.fire({
        title: "Export Failed",
        text: "Failed to export data to CSV",
        icon: "error",
      });
      return false;
    }
  }

  /**
   * Show validation warning dialog before export
   * @param {string} exportType - Type of export (Excel/CSV)
   * @param {Object} validationStatus - Validation status from tableManager
   * @param {Function} continueCallback - Function to call if user confirms
   * @private
   */
  _showValidationWarning(exportType, validationStatus, continueCallback) {
    // Generate HTML for the warning message with issue details
    const warningHtml = `
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
        
        <p>Do you want to export anyway?</p>
      </div>
    `;

    return new Promise((resolve) => {
      Swal.fire({
        title: `Validation Issues Found`,
        html: warningHtml,
        icon: "warning",
        showCancelButton: true,
        confirmButtonText: `Export to ${exportType} anyway`,
        cancelButtonText: "Cancel",
      }).then((result) => {
        if (result.isConfirmed) {
          const exportResult = continueCallback();
          resolve(exportResult);
        } else {
          resolve(false);
        }
      });
    });
  }

  /**
   * Parse and process imported file data
   * @param {File} file - The file to process
   * @returns {Promise<Array>} - The parsed data
   */
  async importFromFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = (e) => {
        try {
          const data = e.target.result;
          const workbook = XLSX.read(data, { type: "binary" });

          // Get the first sheet
          const firstSheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[firstSheetName];

          // Convert to JSON
          let jsonData = XLSX.utils.sheet_to_json(worksheet);

          // Map to our expected format
          jsonData = this.mapImportData(jsonData);

          resolve(jsonData);
        } catch (error) {
          console.error("Error processing file:", error);
          reject(error);
        }
      };

      reader.onerror = (error) => {
        reject(error);
      };

      reader.readAsBinaryString(file);
    });
  }

  /**
   * Map imported data to our expected format
   * @param {Array} data - The imported data
   * @returns {Array} - The mapped data
   */
  mapImportData(data) {
    // Define field mappings (for handling different header names)
    const fieldMappings = {
      // Standard fields
      Name: "name",
      Length: "length",
      Width: "width",
      Height: "height",
      Weight: "weight",
      Quantity: "quantity",
      Fragility: "fragility",
      LoadBear: "loadBear",
      BoxingType: "boxingType",
      Bundle: "bundle",
      "Temperature Sensitivity": "tempSensitivity",

      // Alternative field names
      "Length (m)": "length",
      "Width (m)": "width",
      "Height (m)": "height",
      "Weight (kg)": "weight",
      "Load Bearing (kg)": "loadBear",
      "Load Bearing": "loadBear",
      "Boxing Type": "boxingType",
      "Package Type": "boxingType",
      "Temp Sensitivity": "tempSensitivity",
      "Temperature Range": "tempSensitivity",
    };

    return data.map((item) => {
      const mappedItem = { ...CONFIG.DEFAULT_ROW };

      // Map each field using the mappings
      for (const [importField, standardField] of Object.entries(
        fieldMappings
      )) {
        if (item[importField] !== undefined) {
          mappedItem[standardField] = item[importField];
        }
      }

      // Handle direct field matches
      for (const field of Object.keys(CONFIG.DEFAULT_ROW)) {
        if (item[field] !== undefined) {
          mappedItem[field] = item[field];
        }
      }

      return mappedItem;
    });
  }

  /**
   * Check if export is needed (warns if data hasn't been exported)
   * @param {Array} data - The current data
   * @returns {boolean} - Whether export is needed
   */
  isExportNeeded(data) {
    // If no data, no export needed
    if (!data || data.length === 0) return false;

    // Check last export timestamp
    const lastExport = localStorage.getItem(CONFIG.STORAGE_KEYS.LAST_EXPORT);
    if (!lastExport) return true;

    // Get current data hash (simple approach)
    const currentDataHash = JSON.stringify(data);

    // Get saved data
    const savedData = localStorage.getItem(CONFIG.STORAGE_KEYS.CARGO_DATA);

    // If saved data exists and matches current hash, check timestamp
    if (
      savedData &&
      JSON.stringify(JSON.parse(savedData)) === currentDataHash
    ) {
      // Data hasn't changed since last save, so check timestamp
      const lastExportDate = new Date(lastExport);
      const now = new Date();

      // If last export was within the last hour, no need to export
      return now - lastExportDate > 60 * 60 * 1000;
    }

    // Data has changed since last export
    return true;
  }
}

// Create a global instance
const exportService = new ExportService();
