/**
 * TableManager class to handle the Handsontable functionalities
 */
class TableManager {
  constructor(containerId, columns, defaultRow) {
    this.containerId = containerId;
    this.columns = columns;
    this.defaultRow = defaultRow;
    this.table = null;
    this.data = [{ ...this.defaultRow }];
    this.history = [];
    this.historyPosition = -1;
    this.maxHistoryItems = 50;
    this.validationResults = {};
    this.aiSuggestions = {};
    this.aiFilled = {}; // Track fields that were filled by AI
    this.isInitialized = false;
  }

  /**
   * Initialize the table
   */
  initialize() {
    const container = document.getElementById(this.containerId);
    if (!container) {
      console.error(`Container with ID ${this.containerId} not found`);
      return;
    }

    // Prepare column settings for Handsontable
    const hotColumns = this.columns.map((col) => {
      return {
        data: col.data,
        title: `${col.icon ? `<i class="fas ${col.icon}"></i> ` : ""}${
          col.title
        }${col.required ? " *" : ""}`,
        type: col.type || "text",
        width: col.width || 100,
        readOnly: col.readOnly || false,
        editor: col.type === "dropdown" ? "dropdown" : undefined,
        selectOptions: col.source,
        allowInvalid: true,
        validator: (value, callback) => this.validateCell(col, value, callback),
        renderer: (instance, td, row, col, prop, value, cellProperties) => {
          this.customRenderer(
            instance,
            td,
            row,
            col,
            prop,
            value,
            cellProperties
          );
        },
        // Add dropdown button to dropdown cells
        disableVisualSelection: false,
        // Add dropdown icon to make it clear which fields have dropdowns
        className: col.type === "dropdown" ? "htDropdownCell" : "",
      };
    });

    // Initialize Handsontable
    this.table = new Handsontable(container, {
      data: this.data,
      columns: hotColumns,
      colHeaders: true,
      rowHeaders: true,
      stretchH: "all",
      autoWrapRow: true,
      height: 400,
      licenseKey: "non-commercial-and-evaluation",
      contextMenu: ["row_above", "row_below", "remove_row", "undo", "redo"],
      minSpareRows: 1,
      afterChange: (changes, source) => {
        if (source !== "loadData") {
          this.onDataChange(changes);
          this.saveToLocalStorage();
        }
      },
      afterSelectionEnd: (row, column) => {
        this.showTooltip(row, column);
      },
      beforeKeyDown: (event) => {
        // Handle Ctrl+Z and Ctrl+Y for undo/redo
        if (event.ctrlKey || event.metaKey) {
          if (event.key === "z") {
            event.preventDefault();
            this.undo();
          } else if (event.key === "y") {
            event.preventDefault();
            this.redo();
          }
        }
      },
    });

    this.addHistoryItem(this.data.slice());
    this.isInitialized = true;
  }

  /**
   * Custom renderer for cells
   */
  customRenderer(instance, td, row, col, prop, value, cellProperties) {
    // Default renderer based on cell type
    if (cellProperties.type === "dropdown") {
      Handsontable.renderers.DropdownRenderer.apply(this, arguments);
    } else if (cellProperties.type === "numeric") {
      Handsontable.renderers.NumericRenderer.apply(this, arguments);
    } else {
      Handsontable.renderers.TextRenderer.apply(this, arguments);
    }

    // Apply style based on validation
    const colDef = this.columns.find((c) => c.data === prop);

    if (colDef) {
      // Add validation styling
      const rowData = instance.getSourceDataAtRow(row);
      if (rowData) {
        // Apply fragility-based styling to name field
        if (prop === "name" && rowData.fragility && rowData.name) {
          switch (rowData.fragility) {
            case "LOW":
              td.classList.add("fragility-low");
              break;
            case "MEDIUM":
              td.classList.add("fragility-medium");
              break;
            case "HIGH":
              td.classList.add("fragility-high");
              break;
          }
        }

        const cellKey = `${row}:${prop}`;
        if (this.validationResults[cellKey]) {
          const result = this.validationResults[cellKey];
          if (result.valid === false) {
            td.classList.add("cell-invalid");
            td.setAttribute("title", result.message || "Invalid value");
            // Add error icon for invalid cells
            td.innerHTML +=
              '<span class="validation-icon error-icon">❌</span>';
          } else if (result.warning) {
            td.classList.add("cell-warning");
            td.setAttribute("title", result.message || "Warning");
            // Add warning icon for warning cells
            td.innerHTML +=
              '<span class="validation-icon warning-icon">⚠️</span>';
          }
        }

        // Add AI assisted styling if this field has suggestions
        if (colDef.aiAssisted && this.aiSuggestions[cellKey]) {
          const suggestion = this.aiSuggestions[cellKey];
          const confidence = suggestion.confidence || 0;
          const confidenceLevel = aiService.getConfidenceLevel(confidence);

          td.innerHTML += `<span class="confidence-indicator confidence-${confidenceLevel}" 
                                      title="AI confidence: ${(
                                        confidence * 100
                                      ).toFixed(0)}%">
                                      ${
                                        confidenceLevel === "high"
                                          ? "🟢"
                                          : confidenceLevel === "medium"
                                          ? "🟡"
                                          : "🔴"
                                      }</span>`;
        }

        // Add AI filled indicator
        if (this.aiFilled[cellKey]) {
          td.classList.add("ai-filled");
          // Add a small robot icon to indicate AI filled the field
          td.innerHTML += `<span class="ai-filled-mark" title="Field filled by AI">🤖</span>`;
        }
      }
    }

    // Add required field indicator
    if (colDef && colDef.required && (!value || value === "")) {
      td.classList.add("htInvalid");
    }

    return td;
  }

  /**
   * Validate a cell value
   */
  validateCell(column, value, callback) {
    // Skip validation for empty non-required fields
    if ((value === null || value === "") && !column.required) {
      callback(true);
      return;
    }

    // Required field validation
    if (column.required && (value === null || value === "")) {
      callback(false);
      return;
    }

    // Type-specific validation
    switch (column.data) {
      case "length":
      case "width":
      case "height":
        const dimension = parseFloat(value);
        callback(
          !isNaN(dimension) &&
            dimension >= CONFIG.VALIDATION.MIN_DIMENSIONS &&
            dimension <= CONFIG.VALIDATION.MAX_DIMENSIONS
        );
        break;

      case "weight":
        const weight = parseFloat(value);
        callback(
          !isNaN(weight) &&
            weight >= CONFIG.VALIDATION.MIN_WEIGHT &&
            weight <= CONFIG.VALIDATION.MAX_WEIGHT
        );
        break;

      case "quantity":
        const quantity = parseInt(value);
        callback(
          !isNaN(quantity) &&
            quantity >= CONFIG.VALIDATION.MIN_QUANTITY &&
            quantity <= CONFIG.VALIDATION.MAX_QUANTITY &&
            Number.isInteger(quantity)
        );
        break;

      case "loadBear":
        const loadBear = parseFloat(value);
        callback(
          !isNaN(loadBear) &&
            loadBear >= CONFIG.VALIDATION.MIN_LOADBEAR &&
            loadBear <= CONFIG.VALIDATION.MAX_LOADBEAR
        );
        break;

      case "tempSensitivity":
        callback(
          value === "" || CONFIG.VALIDATION.TEMP_SENSITIVITY_PATTERN.test(value)
        );
        break;

      case "fragility":
        callback(value === "LOW" || value === "MEDIUM" || value === "HIGH");
        break;

      case "boxingType":
        callback(
          ["BOX", "PALLET", "LOOSE", "CONTAINER", "CRATE"].includes(value)
        );
        break;

      case "bundle":
        callback(value === "YES" || value === "NO");
        break;

      default:
        callback(true);
    }
  }

  /**
   * Handle data changes
   */
  async onDataChange(changes) {
    if (!changes) return;

    // Process each changed cell
    for (const [row, prop, oldValue, newValue] of changes) {
      // Skip empty changes
      if (oldValue === newValue) continue;

      const item = this.data[row];
      const columnDef = this.columns.find((col) => col.data === prop);

      if (!columnDef) continue;

      // If a name was changed, trigger AI suggestions
      if (prop === "name" && newValue && newValue !== "") {
        this.requestAiSuggestions(row, item);
      }

      // Add to history
      this.addHistoryItem(this.data.slice());

      // Validate the changed field
      await this.validateField(row, prop, newValue);
    }

    // Update UI
    this.updateUndoRedoButtons();
    this.table.render();
  }

  /**
   * Request AI suggestions for a row
   */
  async requestAiSuggestions(rowIndex, item) {
    console.log(`Requesting AI suggestions for row ${rowIndex}:`, item);

    // Skip if name is empty
    if (!item.name || item.name.trim() === "") {
      console.log("Skipping AI suggestion request - empty item name");
      return;
    }

    // Get context from previous items
    const context = this.data
      .filter(
        (dataItem, idx) =>
          idx !== rowIndex &&
          dataItem.name &&
          dataItem.fragility &&
          dataItem.loadBear &&
          dataItem.tempSensitivity
      )
      .slice(0, CONFIG.AI.MAX_CONTEXT_ITEMS);

    console.log(`Found ${context.length} context items for AI suggestions`);

    // Get suggestions from AI service
    try {
      console.log("Calling AI service for suggestions...");
      const suggestions = await aiService.getSuggestions(item, context);
      console.log("AI suggestions received:", suggestions);

      if (suggestions) {
        // Store suggestions for fields that need assistance
        const aiAssistedFields = this.columns
          .filter((col) => col.aiAssisted)
          .map((col) => col.data);

        console.log("AI-assisted fields:", aiAssistedFields);

        for (const field of aiAssistedFields) {
          if (suggestions[field]) {
            console.log(`Adding suggestion for ${field}:`, suggestions[field]);
            this.aiSuggestions[`${rowIndex}:${field}`] = suggestions[field];

            // If the field is empty, auto-fill with high confidence suggestions
            if (
              (!item[field] || item[field] === "") &&
              suggestions[field].confidence >=
                CONFIG.AI.CONFIDENCE_THRESHOLDS.HIGH
            ) {
              console.log(
                `Auto-filling ${field} with high confidence value:`,
                suggestions[field].value
              );
              this.table.setDataAtRowProp(
                rowIndex,
                field,
                suggestions[field].value
              );

              // Mark this field as filled by AI
              this.aiFilled[`${rowIndex}:${field}`] = true;
            }
          } else {
            console.log(`No suggestion available for ${field}`);
          }
        }

        // Update the suggestions panel
        this.updateSuggestionsPanel(rowIndex, suggestions);

        // Re-render the table
        this.table.render();
        console.log("Table re-rendered after applying suggestions");
      } else {
        console.warn("AI service returned no suggestions");
      }
    } catch (error) {
      console.error("Error getting AI suggestions:", error);
      // Show error notification to user
      Swal.fire({
        title: "AI Suggestion Error",
        text: "Could not get AI suggestions at this time. Please try again later.",
        icon: "error",
        timer: 3000,
        toast: true,
        position: "top-end",
        showConfirmButton: false,
      });
    }
  }

  /**
   * Update the AI suggestions panel
   */
  updateSuggestionsPanel(rowIndex, suggestions) {
    const suggestionsPanel = document.getElementById("aiSuggestions");
    if (!suggestionsPanel) {
      console.error("Suggestions panel element not found in the DOM");
      return;
    }

    // Clear existing content if this is the first suggestion
    if (suggestionsPanel.querySelector(".text-muted")) {
      suggestionsPanel.innerHTML = "";
    }

    const itemName = this.data[rowIndex].name;
    if (!itemName) return;

    // Create suggestion item for this row
    const suggestionItem = document.createElement("div");
    suggestionItem.className = "ai-suggestion-item fade-in";
    suggestionItem.setAttribute("data-row", rowIndex);

    let content = `<h5>${itemName}</h5><div class="suggestion-content">`;

    // Add each field suggestion
    for (const field in suggestions) {
      // Skip if no data
      if (!suggestions[field] || !suggestions[field].value) continue;

      const confidence = suggestions[field].confidence || 0;
      const confidenceLevel = aiService.getConfidenceLevel(confidence);
      const confidenceIcon =
        confidenceLevel === "high"
          ? "🟢"
          : confidenceLevel === "medium"
          ? "🟡"
          : "🔴";

      content += `
                <div class="suggestion-field mb-2">
                    <div>
                        <strong>${
                          this.columns.find((col) => col.data === field)
                            ?.title || field
                        }:</strong> 
                        <span class="confidence-${confidenceLevel}">
                            ${confidenceIcon} ${(confidence * 100).toFixed(
        0
      )}% confident
                        </span>
                    </div>
                    <div class="suggestion-value">${
                      suggestions[field].value
                    }</div>
                    <div class="text-muted small">${
                      suggestions[field].reasoning || ""
                    }</div>
                    <button class="btn btn-sm btn-outline-primary mt-1 apply-suggestion" 
                        data-row="${rowIndex}" data-field="${field}" data-value="${
        suggestions[field].value
      }">
                        Apply
                    </button>
                </div>
            `;
    }

    content += "</div>";
    suggestionItem.innerHTML = content;

    // Add event listeners to apply buttons
    suggestionItem.querySelectorAll(".apply-suggestion").forEach((button) => {
      button.addEventListener("click", (e) => {
        const row = parseInt(e.target.getAttribute("data-row"));
        const field = e.target.getAttribute("data-field");
        const value = e.target.getAttribute("data-value");
        this.table.setDataAtRowProp(row, field, value);

        // Mark field as filled by AI
        this.aiFilled[`${row}:${field}`] = true;

        e.target.disabled = true;
        e.target.textContent = "Applied";
        e.target.classList.remove("btn-outline-primary");
        e.target.classList.add("btn-success");

        // Re-render to show AI filled indicator
        this.table.render();
      });
    });

    // Add suggestion to panel (newest first)
    suggestionsPanel.insertBefore(suggestionItem, suggestionsPanel.firstChild);

    // Limit number of visible suggestions
    const allSuggestions = suggestionsPanel.querySelectorAll(
      ".ai-suggestion-item"
    );
    if (allSuggestions.length > 5) {
      for (let i = 5; i < allSuggestions.length; i++) {
        allSuggestions[i].remove();
      }
    }
  }

  /**
   * Validate a specific field
   */
  async validateField(rowIndex, field, value) {
    const item = this.data[rowIndex];
    const cellKey = `${rowIndex}:${field}`;

    // Skip validation for empty items
    if (!item.name) {
      this.validationResults[cellKey] = { valid: true };
      return;
    }

    // Regular validation rules
    const columnDef = this.columns.find((col) => col.data === field);
    if (!columnDef) return;

    // Basic format validation
    if (value === null || value === "") {
      if (columnDef.required) {
        this.validationResults[cellKey] = {
          valid: false,
          message: "This field is required",
        };
      } else {
        this.validationResults[cellKey] = { valid: true };
      }
      return;
    }

    // Type-specific validation
    let validationResult = { valid: true };

    switch (field) {
      case "length":
      case "width":
      case "height":
        const dimension = parseFloat(value);
        if (isNaN(dimension)) {
          validationResult = {
            valid: false,
            message: "Must be a number",
          };
        } else if (dimension < CONFIG.VALIDATION.MIN_DIMENSIONS) {
          validationResult = {
            valid: false,
            message: `Min dimension: ${CONFIG.VALIDATION.MIN_DIMENSIONS}m`,
          };
        } else if (dimension > CONFIG.VALIDATION.MAX_DIMENSIONS) {
          validationResult = {
            valid: false,
            message: `Max dimension: ${CONFIG.VALIDATION.MAX_DIMENSIONS}m`,
          };
        }
        break;

      case "weight":
        const weight = parseFloat(value);
        if (isNaN(weight)) {
          validationResult = {
            valid: false,
            message: "Must be a number",
          };
        } else if (weight < CONFIG.VALIDATION.MIN_WEIGHT) {
          validationResult = {
            valid: false,
            message: `Min weight: ${CONFIG.VALIDATION.MIN_WEIGHT}kg`,
          };
        } else if (weight > CONFIG.VALIDATION.MAX_WEIGHT) {
          validationResult = {
            valid: false,
            message: `Max weight: ${CONFIG.VALIDATION.MAX_WEIGHT}kg`,
          };
        }
        break;

      case "quantity":
        const quantity = parseInt(value);
        if (isNaN(quantity) || !Number.isInteger(quantity)) {
          validationResult = {
            valid: false,
            message: "Must be a whole number",
          };
        } else if (quantity < CONFIG.VALIDATION.MIN_QUANTITY) {
          validationResult = {
            valid: false,
            message: `Min quantity: ${CONFIG.VALIDATION.MIN_QUANTITY}`,
          };
        } else if (quantity > CONFIG.VALIDATION.MAX_QUANTITY) {
          validationResult = {
            valid: false,
            message: `Max quantity: ${CONFIG.VALIDATION.MAX_QUANTITY}`,
          };
        }
        break;

      case "loadBear":
        const loadBear = parseFloat(value);
        if (value && isNaN(loadBear)) {
          validationResult = {
            valid: false,
            message: "Must be a number",
          };
        } else if (loadBear < CONFIG.VALIDATION.MIN_LOADBEAR) {
          validationResult = {
            valid: false,
            message: `Min load bearing: ${CONFIG.VALIDATION.MIN_LOADBEAR}kg`,
          };
        } else if (loadBear > CONFIG.VALIDATION.MAX_LOADBEAR) {
          validationResult = {
            valid: false,
            message: `Max load bearing: ${CONFIG.VALIDATION.MAX_LOADBEAR}kg`,
          };
        }
        break;

      case "tempSensitivity":
        if (value && !CONFIG.VALIDATION.TEMP_SENSITIVITY_PATTERN.test(value)) {
          validationResult = {
            valid: false,
            message: "Format: 10°C to 30°C",
          };
        }
        break;

      case "fragility":
        if (value && !["LOW", "MEDIUM", "HIGH"].includes(value)) {
          validationResult = {
            valid: false,
            message: "Must be LOW, MEDIUM, or HIGH",
          };
        }
        break;

      case "boxingType":
        if (
          value &&
          !["BOX", "PALLET", "LOOSE", "CONTAINER", "CRATE"].includes(value)
        ) {
          validationResult = {
            valid: false,
            message: "Invalid boxing type",
          };
        }
        break;

      case "bundle":
        if (value && !["YES", "NO"].includes(value)) {
          validationResult = {
            valid: false,
            message: "Must be YES or NO",
          };
        }
        break;
    }

    // Update validation results
    this.validationResults[cellKey] = validationResult;

    // If row has substantial data, use AI validation for more complex checks
    if (
      item.name &&
      // Check if enough fields are filled to warrant validation
      ((item.length && item.width && item.height && item.weight) ||
        (field === "fragility" && item.loadBear) ||
        field === "tempSensitivity")
    ) {
      try {
        console.log("Calling AI validation for item", item);
        const validationIssues = await aiService.validateItem(item);
        console.log("AI validation results:", validationIssues);

        // Process validation issues
        for (const issue of validationIssues) {
          if (issue.field === field) {
            // Override the validation for this field
            this.validationResults[cellKey] = {
              valid: issue.severity !== "error",
              warning: issue.severity === "warning",
              message: issue.message,
              confidence: issue.confidence,
            };

            // Update validation feedback panel
            this.updateValidationPanel(rowIndex, field, issue);
          }
        }
      } catch (error) {
        console.error("Error in AI validation:", error);
        // Don't silently fail - show a warning in UI
        Swal.fire({
          title: "Validation Warning",
          text: "Could not perform advanced validation. Basic validation will still apply.",
          icon: "warning",
          toast: true,
          position: "top-end",
          showConfirmButton: false,
          timer: 3000,
        });
      }
    }
  }

  /**
   * Update the validation feedback panel
   */
  updateValidationPanel(rowIndex, field, issue) {
    const validationPanel = document.getElementById("validationFeedback");
    if (!validationPanel) return;

    // Clear existing content if this is the first validation
    if (validationPanel.querySelector(".text-muted")) {
      validationPanel.innerHTML = "";
    }

    const itemName = this.data[rowIndex].name;
    if (!itemName) return;

    // Create validation item
    const validationItem = document.createElement("div");
    validationItem.className = `validation-item validation-${issue.severity} fade-in`;
    validationItem.setAttribute("data-row", rowIndex);
    validationItem.setAttribute("data-field", field);

    const icon =
      issue.severity === "error"
        ? '<i class="fas fa-exclamation-circle"></i>'
        : '<i class="fas fa-exclamation-triangle"></i>';

    validationItem.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    ${icon}
                    <strong>${itemName}:</strong> 
                    <span class="validation-message">${issue.message}</span>
                    <div class="small text-muted">
                        Field: ${
                          this.columns.find((col) => col.data === field)
                            ?.title || field
                        }
                    </div>
                </div>
                <button class="btn btn-sm btn-outline-secondary ms-2 view-item" 
                    data-row="${rowIndex}">View</button>
            </div>
        `;

    // Add event listener for view button
    validationItem
      .querySelector(".view-item")
      .addEventListener("click", (e) => {
        const row = parseInt(e.target.getAttribute("data-row"));
        this.table.selectCell(
          row,
          this.columns.findIndex((col) => col.data === field)
        );

        // Show the table tab
        const requiredTab = document.getElementById("required-tab");
        if (requiredTab) {
          const tabInstance = new bootstrap.Tab(requiredTab);
          tabInstance.show();
        }
      });

    // Add validation to panel (newest first)
    validationPanel.insertBefore(validationItem, validationPanel.firstChild);

    // Limit number of visible validations
    const allValidations = validationPanel.querySelectorAll(".validation-item");
    if (allValidations.length > 5) {
      for (let i = 5; i < allValidations.length; i++) {
        allValidations[i].remove();
      }
    }
  }

  /**
   * Show tooltip for a cell
   */
  showTooltip(row, column) {
    // Remove any existing tooltips
    const existingTooltip = document.querySelector(".custom-tooltip");
    if (existingTooltip) {
      existingTooltip.remove();
    }

    // Get the column definition
    const prop = this.table.colToProp(column);
    const columnDef = this.columns.find((col) => col.data === prop);

    if (!columnDef || !columnDef.tooltip) return;

    // Create tooltip
    const tooltip = document.createElement("div");
    tooltip.className = "custom-tooltip fade-in";
    tooltip.innerText = columnDef.tooltip;
    document.body.appendChild(tooltip);

    // Position tooltip near the cell
    const cellRect = this.table.getCell(row, column).getBoundingClientRect();
    tooltip.style.left = `${
      cellRect.left + cellRect.width / 2 - tooltip.offsetWidth / 2
    }px`;
    tooltip.style.top = `${cellRect.top - tooltip.offsetHeight - 5}px`;

    // Remove tooltip after a delay
    setTimeout(() => {
      if (tooltip.parentNode) {
        tooltip.classList.remove("fade-in");
        tooltip.classList.add("fade-out");
        setTimeout(() => {
          if (tooltip.parentNode) {
            tooltip.remove();
          }
        }, 300);
      }
    }, 3000);
  }

  /**
   * Add an item to the history
   */
  addHistoryItem(data) {
    // Don't add if identical to current state
    if (
      this.historyPosition >= 0 &&
      JSON.stringify(this.history[this.historyPosition]) ===
        JSON.stringify(data)
    ) {
      return;
    }

    // If we're not at the end of the history, truncate it
    if (this.historyPosition < this.history.length - 1) {
      this.history = this.history.slice(0, this.historyPosition + 1);
    }

    // Add new history item
    this.history.push(JSON.parse(JSON.stringify(data)));

    // Limit history size
    if (this.history.length > this.maxHistoryItems) {
      this.history.shift();
    } else {
      this.historyPosition++;
    }

    this.updateUndoRedoButtons();
  }

  /**
   * Undo the last action
   */
  undo() {
    if (this.historyPosition <= 0) return;

    this.historyPosition--;
    this.data = JSON.parse(JSON.stringify(this.history[this.historyPosition]));
    this.table.loadData(this.data);
    this.updateUndoRedoButtons();
  }

  /**
   * Redo the last undone action
   */
  redo() {
    if (this.historyPosition >= this.history.length - 1) return;

    this.historyPosition++;
    this.data = JSON.parse(JSON.stringify(this.history[this.historyPosition]));
    this.table.loadData(this.data);
    this.updateUndoRedoButtons();
  }

  /**
   * Update the undo/redo buttons state
   */
  updateUndoRedoButtons() {
    const undoButton = document.getElementById("undoButton");
    const redoButton = document.getElementById("redoButton");

    if (undoButton) {
      undoButton.disabled = this.historyPosition <= 0;
    }

    if (redoButton) {
      redoButton.disabled = this.historyPosition >= this.history.length - 1;
    }
  }

  /**
   * Save data to localStorage
   */
  saveToLocalStorage() {
    if (!this.isInitialized) return;

    try {
      // Filter out empty rows
      const dataToSave = this.data.filter((item) => item.name);
      localStorage.setItem(
        CONFIG.STORAGE_KEYS.CARGO_DATA,
        JSON.stringify(dataToSave)
      );
    } catch (error) {
      console.error("Error saving to localStorage:", error);
    }
  }

  /**
   * Load data from localStorage
   */
  loadFromLocalStorage() {
    try {
      const savedData = localStorage.getItem(CONFIG.STORAGE_KEYS.CARGO_DATA);
      if (savedData) {
        const parsedData = JSON.parse(savedData);
        if (Array.isArray(parsedData) && parsedData.length > 0) {
          // Add an empty row if needed
          if (!parsedData.some((item) => !item.name)) {
            parsedData.push({ ...this.defaultRow });
          }
          this.data = parsedData;
          if (this.table) {
            this.table.loadData(this.data);
            this.addHistoryItem(this.data.slice());
          }
          return true;
        }
      }
    } catch (error) {
      console.error("Error loading from localStorage:", error);
      return false;
    }
    return false;
  }

  /**
   * Clear all data
   */
  clearData() {
    this.data = [{ ...this.defaultRow }];
    if (this.table) {
      this.table.loadData(this.data);
      this.addHistoryItem(this.data.slice());
      this.saveToLocalStorage();
    }
  }

  /**
   * Get the current data
   */
  getData() {
    return this.data.filter((item) => item.name);
  }

  /**
   * Add a new row
   */
  addRow() {
    this.data.push({ ...this.defaultRow });
    this.table.loadData(this.data);
    this.addHistoryItem(this.data.slice());
    this.saveToLocalStorage();
  }

  /**
   * Remove selected rows
   */
  removeSelectedRows() {
    const selected = this.table.getSelected();
    if (!selected || selected.length === 0) return;

    const rowsToRemove = [];
    for (const selection of selected) {
      const [startRow, , endRow] = selection;
      for (let row = startRow; row <= endRow; row++) {
        if (!rowsToRemove.includes(row)) {
          rowsToRemove.push(row);
        }
      }
    }

    // Sort in reverse order to avoid index shifting
    rowsToRemove.sort((a, b) => b - a);

    // Remove rows
    for (const row of rowsToRemove) {
      this.data.splice(row, 1);
    }

    // Add empty row if all rows were deleted
    if (this.data.length === 0) {
      this.data.push({ ...this.defaultRow });
    }

    this.table.loadData(this.data);
    this.addHistoryItem(this.data.slice());
    this.saveToLocalStorage();
  }

  setDataFromFile(fileData) {
    // Filter out empty rows
    const validRows = fileData.filter((item) => item.name);
    this.data = [...validRows];

    // Ensure there's an empty row at the end
    if (!this.data.some((item) => !item.name)) {
      this.data.push({ ...this.defaultRow });
    }

    this.table.loadData(this.data);
    this.addHistoryItem(this.data.slice());
    this.saveToLocalStorage();

    // Request AI suggestions for all rows
    for (let i = 0; i < validRows.length; i++) {
      if (validRows[i].name) {
        this.requestAiSuggestions(i, validRows[i]);
      }
    }
  }

  /**
   * Show AI suggestion modal for filling missing fields
   */
  async showAiFillModal() {
    const items = this.data.filter((item) => item.name);
    if (items.length === 0) {
      Swal.fire({
        title: "No Data",
        text: "Please add cargo items before using AI assistance",
        icon: "info",
      });
      return;
    }

    Swal.fire({
      title: "AI Processing",
      html: "Analyzing your cargo data...",
      allowOutsideClick: false,
    });

    // Show loading
    Swal.showLoading();

    // Get AI suggestions for all items
    const allSuggestions = await aiService.fillMissingFields(items);

    try {
      // Close loading dialog
      Swal.close();

      // If no suggestions, show message
      if (Object.keys(allSuggestions).length === 0) {
        Swal.fire({
          title: "No Suggestions",
          text: "AI could not generate any suggestions for your cargo items",
          icon: "info",
        });
        return;
      }

      // Populate suggestion modal
      const suggestionList = document.getElementById("aiSuggestionList");
      if (!suggestionList) return;

      suggestionList.innerHTML = ""; // Clear existing content

      for (const rowIndex in allSuggestions) {
        const itemSuggestions = allSuggestions[rowIndex].suggestions;
        const item = allSuggestions[rowIndex].item;
        let content = `<h6>${item.name}</h6>`;
        const suggestionRow = document.createElement("div");
        suggestionRow.className = "suggestion-row";

        for (const field in itemSuggestions) {
          const suggestion = itemSuggestions[field];
          const confidence = suggestion.confidence || 0;
          const confidenceLevel = aiService.getConfidenceLevel(confidence);
          const confidenceIcon =
            confidenceLevel === "high"
              ? "🟢"
              : confidenceLevel === "medium"
              ? "🟡"
              : "🔴";

          content += `
                <div class="suggestion-field">
                    ${
                      this.columns.find((col) => col.data === field)?.title ||
                      field
                    }:
                    <span class="confidence-${confidenceLevel}">
                        ${confidenceIcon} ${(confidence * 100).toFixed(
            0
          )}% confident
                    </span>
                    <div class="suggestion-value">${suggestion.value}</div>
                    <div class="form-check form-switch mt-1">
                      <input class="form-check-input suggestion-checkbox" type="checkbox" 
                        id="suggestion-${rowIndex}-${field}" 
                        data-row="${rowIndex}" data-field="${field}" data-value="${
            suggestion.value
          }"
                        ${
                          confidence >= CONFIG.AI.CONFIDENCE_THRESHOLDS.HIGH
                            ? "checked"
                            : ""
                        }
                      >
                      <label class="form-check-label" for="suggestion-${rowIndex}-${field}">
                        Apply this suggestion
                      </label>
                    </div>
                </div>
            `;
        }

        suggestionRow.innerHTML = content;
        suggestionList.appendChild(suggestionRow);
      }

      // Show modal
      const modal = new bootstrap.Modal(
        document.getElementById("aiSuggestionModal")
      );
      const acceptAllButton = document.getElementById("acceptAllSuggestions");
      modal.show();

      // Add event listener for Accept All button
      if (acceptAllButton) {
        acceptAllButton.onclick = () => {
          this.applyAllSuggestions();
          modal.hide();
        };
      }
    } catch (error) {
      console.error("Error getting AI fill suggestions:", error);
      Swal.fire({
        title: "Error",
        text: "Could not generate AI suggestions. Please try again.",
        icon: "error",
      });
    }
  }

  /**
   * Apply all checked suggestions from the modal
   */
  applyAllSuggestions() {
    const checkboxes = document.querySelectorAll(
      ".suggestion-checkbox:checked"
    );

    const changedRows = new Set();

    checkboxes.forEach((checkbox) => {
      const row = parseInt(checkbox.getAttribute("data-row"));
      const field = checkbox.getAttribute("data-field");
      const value = checkbox.getAttribute("data-value");
      this.table.setDataAtRowProp(row, field, value);

      // Mark fields applied from suggestions as AI filled
      this.aiFilled[`${row}:${field}`] = true;

      // Track which rows changed
      changedRows.add(row);
    });

    // Add to history
    this.addHistoryItem(this.data.slice());

    // Save to localStorage
    this.saveToLocalStorage();

    // Revalidate all affected rows
    changedRows.forEach((row) => {
      const item = this.data[row];
      if (item.name) {
        Object.keys(item).forEach((field) => {
          this.validateField(row, field, item[field]);
        });
      }
    });

    // Re-render to show AI filled indicators
    this.table.render();

    Swal.fire({
      title: "Success",
      text: `Applied ${checkboxes.length} AI suggestions`,
      icon: "success",
      timer: 2000,
      showConfirmButton: false,
    });
  }

  /**
   * Force AI suggestions for a specific row
   */
  async forceAiSuggestionsForRow(rowIndex) {
    if (rowIndex < 0 || rowIndex >= this.data.length) {
      console.error(`Invalid row index: ${rowIndex}`);
      return false;
    }

    const item = this.data[rowIndex];
    console.log(`Forcing AI suggestions for row ${rowIndex}:`, item);

    try {
      await this.requestAiSuggestions(rowIndex, item);
      return true;
    } catch (error) {
      console.error(`Error forcing AI suggestions for row ${rowIndex}:`, error);
      return false;
    }
  }

  /**
   * Create a read-only preview table
   */
  createPreviewTable(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Get valid data
    const validData = this.getData();

    // Create the preview table
    new Handsontable(container, {
      data: validData,
      columns: this.columns.map((col) => {
        return {
          data: col.data,
          title: col.title,
          readOnly: true,
        };
      }),
      colHeaders: true,
      rowHeaders: true,
      stretchH: "all",
      readOnly: true,
      licenseKey: "non-commercial-and-evaluation",
    });
  }

  /**
   * Update the data statistics
   */
  updateDataStats(data) {
    const statsContainer = document.getElementById("dataStats");
    if (!statsContainer) return;

    // Calculate statistics
    const totalItems = data.reduce(
      (sum, item) => sum + (parseInt(item.quantity) || 0),
      0
    );
    const uniqueItems = data.length;
    const totalWeight = data.reduce((sum, item) => {
      const weight = parseFloat(item.weight) || 0;
      const quantity = parseInt(item.quantity) || 0;
      return sum + weight * quantity;
    }, 0);

    // Create stats cards
    statsContainer.innerHTML = `
            <div class="row">
                <div class="col-md-4">
                    <div class="stat-card">
                        <div class="stat-value">${uniqueItems}</div>
                        <div class="stat-label">Unique Cargo Types</div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stat-card">
                        <div class="stat-value">${totalItems}</div>
                        <div class="stat-label">Total Cargo Items</div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="stat-card">
                        <div class="stat-value">${totalWeight.toFixed(
                          2
                        )} kg</div>
                        <div class="stat-label">Total Cargo Weight</div>
                    </div>
                </div>
            </div>
        `;
  }

  /**
   * Get validation status for all data
   * @returns {Object} - Object with validation stats and issues
   */
  getValidationStatus() {
    const issues = [];
    const itemsWithIssues = new Set();

    // Check all validation results
    for (const [cellKey, result] of Object.entries(this.validationResults)) {
      if (!result.valid || result.warning) {
        const [rowIndex, field] = cellKey.split(":");
        const row = parseInt(rowIndex);

        // Get item name for the issue
        const itemName = this.data[row]?.name || `Item #${row + 1}`;

        // Add to issues list
        issues.push({
          itemName,
          field,
          message: result.message || (result.valid ? "Warning" : "Error"),
          severity: result.valid ? "warning" : "error",
          row,
        });

        // Track unique items with issues
        itemsWithIssues.add(row);
      }
    }

    return {
      hasIssues: issues.length > 0,
      totalIssues: issues.length,
      itemsAffected: itemsWithIssues.size,
      issues: issues,
    };
  }
}
