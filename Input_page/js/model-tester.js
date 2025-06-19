/**
 * Gemini Model Tester for GravitycARgo
 * This utility helps test different configurations for the Gemini 2.5 Flash Preview model
 */

class GeminiModelTester {
  constructor() {
    this.testItems = [
      {
        name: "Standard Wooden Pallet",
        length: 1.2,
        width: 1.0,
        height: 0.15,
        weight: 25,
      },
      {
        name: "Medical Equipment (Fragile)",
        length: 0.6,
        width: 0.4,
        height: 0.3,
        weight: 8,
      },
      {
        name: "Industrial Machine Parts",
        length: 1.8,
        width: 0.9,
        height: 0.7,
        weight: 560,
      },
      {
        name: "Fresh Produce",
        length: 0.6,
        width: 0.4,
        height: 0.2,
        weight: 12,
      },
      {
        name: "Computer Servers",
        length: 0.8,
        width: 0.6,
        height: 0.2,
        weight: 25,
      },
    ];

    // Configuration parameters to test
    this.configurations = [
      {
        temperature: 0.2,
        topK: 40,
        topP: 0.95,
        description: "Low temperature (more focused)",
      },
      {
        temperature: 0.7,
        topK: 40,
        topP: 0.95,
        description: "High temperature (more creative)",
      },
      {
        temperature: 0.4,
        topK: 40,
        topP: 0.95,
        description: "Balanced temperature",
      },
    ];

    this.results = {};
    this.currentTest = null;
  }

  /**
   * Create and display the model tester UI
   */
  createUI() {
    // Create container for test UI
    const container = document.createElement("div");
    container.id = "modelTesterContainer";
    container.className = "model-tester-container card position-fixed";
    container.style.right = "20px";
    container.style.top = "80px";
    container.style.width = "350px";
    container.style.zIndex = "1000";
    container.style.display = "none";

    container.innerHTML = `
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                <h5 class="mb-0">Gemini Model Configuration Tester</h5>
                <button type="button" class="btn-close btn-close-white" id="closeTesterBtn"></button>
            </div>
            <div class="card-body">
                <div class="mb-3">
                    <label class="form-label">Select Configuration(s) to Test:</label>
                    <div class="config-checkboxes">
                        ${this.configurations
                          .map(
                            (config, index) => `
                            <div class="form-check">
                                <input class="form-check-input config-checkbox" type="checkbox" value="${index}" id="config-${index}" checked>
                                <label class="form-check-label" for="config-${index}">
                                    ${config.description} (temp=${config.temperature})
                                </label>
                            </div>
                        `
                          )
                          .join("")}
                    </div>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">Test Type:</label>
                    <select class="form-select" id="testTypeSelect">
                        <option value="suggestions">Field Suggestions</option>
                        <option value="validation">Data Validation</option>
                    </select>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">Test Item:</label>
                    <select class="form-select" id="testItemSelect">
                        ${this.testItems
                          .map(
                            (item, index) => `
                            <option value="${index}">${item.name}</option>
                        `
                          )
                          .join("")}
                    </select>
                </div>
                
                <button class="btn btn-primary w-100" id="runModelTestBtn">
                    Run Test
                </button>
                
                <div class="test-results mt-3" id="modelTestResults">
                    <div class="text-center text-muted py-3">
                        <small>Test results will appear here</small>
                    </div>
                </div>
            </div>
        `;

    document.body.appendChild(container);

    // Add toggle button
    const toggleBtn = document.createElement("button");
    toggleBtn.id = "toggleModelTesterBtn";
    toggleBtn.className = "btn btn-primary position-fixed";
    toggleBtn.style.right = "20px";
    toggleBtn.style.top = "20px";
    toggleBtn.style.zIndex = "1000";
    toggleBtn.innerHTML = '<i class="fas fa-flask"></i> Config Tester';
    document.body.appendChild(toggleBtn);

    // Add event listeners
    toggleBtn.addEventListener("click", () => {
      const tester = document.getElementById("modelTesterContainer");
      if (tester) {
        tester.style.display =
          tester.style.display === "none" ? "block" : "none";
      }
    });

    document.getElementById("closeTesterBtn").addEventListener("click", () => {
      const tester = document.getElementById("modelTesterContainer");
      if (tester) {
        tester.style.display = "none";
      }
    });

    document.getElementById("runModelTestBtn").addEventListener("click", () => {
      this.runSelectedTest();
    });
  }

  /**
   * Run the selected test based on UI settings
   */
  async runSelectedTest() {
    const testType = document.getElementById("testTypeSelect").value;
    const itemIndex = parseInt(document.getElementById("testItemSelect").value);
    const selectedConfigs = [];

    // Get selected configurations
    document
      .querySelectorAll(".config-checkbox:checked")
      .forEach((checkbox) => {
        const configIndex = parseInt(checkbox.value);
        selectedConfigs.push(this.configurations[configIndex]);
      });

    if (selectedConfigs.length === 0) {
      this.showTestResults(
        "error",
        "Please select at least one configuration to test"
      );
      return;
    }

    const testItem = this.testItems[itemIndex];

    // Update UI to show test is running
    this.showTestResults(
      "loading",
      `Testing ${selectedConfigs.length} configurations with ${testItem.name}...`
    );

    try {
      switch (testType) {
        case "suggestions":
          await this.runSuggestionsTest(selectedConfigs, testItem);
          break;
        case "validation":
          await this.runValidationTest(selectedConfigs, testItem);
          break;
      }
    } catch (error) {
      console.error("Test error:", error);
      this.showTestResults("error", `Test failed: ${error.message}`);
    }
  }

  /**
   * Run field suggestions test
   */
  async runSuggestionsTest(configurations, item) {
    const results = {};

    for (const config of configurations) {
      // Update UI
      this.showTestResults(
        "loading",
        `Testing configuration: ${config.description}...`
      );

      // Run test
      try {
        const startTime = performance.now();
        const suggestions = await aiService.getSuggestionsWithConfig(
          item,
          [],
          config
        );
        const endTime = performance.now();

        results[config.description] = {
          success: !!suggestions,
          responseTime: Math.round(endTime - startTime),
          data: suggestions,
          config: config,
        };
      } catch (error) {
        results[config.description] = {
          success: false,
          error: error.message,
          config: config,
        };
      }
    }

    // Display results
    this.displaySuggestionsResults(results, item);
  }

  /**
   * Run validation test
   */
  async runValidationTest(configurations, item) {
    // Currently the validation function doesn't use configurations,
    // but keeping this separate in case we implement different validation configs
    const results = {};

    // Create a problematic item for validation test
    const testItem = {
      ...item,
      fragility: "LOW", // Intentionally questionable for validation
      loadBear: item.weight * 100, // Unrealistically high load-bearing capacity
      tempSensitivity: "15°C to 35°C",
    };

    // Update UI
    this.showTestResults(
      "loading",
      `Testing validation with ${testItem.name}...`
    );

    // Run validation test
    try {
      const startTime = performance.now();
      const issues = await aiService.validateItem(testItem);
      const endTime = performance.now();

      results["standard"] = {
        success: true,
        responseTime: Math.round(endTime - startTime),
        issueCount: issues.length,
        data: issues,
      };
    } catch (error) {
      results["standard"] = {
        success: false,
        error: error.message,
      };
    }

    // Display results
    this.displayValidationResults(results, testItem);
  }

  /**
   * Display suggestions test results
   */
  displaySuggestionsResults(results, item) {
    let html = `<h6 class="mt-2 mb-3">Configuration Test Results</h6>
                    <div class="small mb-2">Test item: ${item.name}</div>`;

    // Create comparison summary
    html += `<table class="table table-sm table-bordered">
                  <thead>
                    <tr>
                      <th>Configuration</th>
                      <th>Time (ms)</th>
                      <th>Result</th>
                    </tr>
                  </thead>
                  <tbody>`;

    for (const [description, result] of Object.entries(results)) {
      html += `<tr>
                      <td>${description}</td>
                      <td>${result.success ? result.responseTime : "N/A"}</td>
                      <td>
                        <span class="badge ${
                          result.success ? "bg-success" : "bg-danger"
                        }">
                          ${result.success ? "Success" : "Failed"}
                        </span>
                      </td>
                    </tr>`;
    }

    html += `</tbody></table>`;

    // Show detailed results for each configuration
    for (const [description, result] of Object.entries(results)) {
      html += `<div class="result-card mb-3 p-2 border rounded">
                      <div class="d-flex justify-content-between">
                        <strong>${description}</strong>
                        <span class="badge ${
                          result.success ? "bg-success" : "bg-danger"
                        }">
                          ${result.success ? "Success" : "Failed"}
                        </span>
                      </div>
                      <div class="small text-muted">
                        Temperature: ${result.config.temperature},
                        TopK: ${result.config.topK},
                        TopP: ${result.config.topP}
                      </div>`;

      if (result.success) {
        html += `<div class="text-muted small">Response time: ${result.responseTime}ms</div>`;

        if (result.data) {
          // Display suggestions
          for (const field of ["fragility", "loadBear", "tempSensitivity"]) {
            if (result.data[field]) {
              const suggestion = result.data[field];
              const confidenceLevel = aiService.getConfidenceLevel(
                suggestion.confidence
              );
              const confidenceIcon =
                confidenceLevel === "high"
                  ? "🟢"
                  : confidenceLevel === "medium"
                  ? "🟡"
                  : "🔴";

              html += `<div class="suggestion-item mt-2">
                                      <div class="fw-bold small">${field}:</div>
                                      <div class="d-flex justify-content-between align-items-center">
                                        <code>${suggestion.value}</code>
                                        <span class="confidence-${confidenceLevel} small">
                                          ${confidenceIcon} ${Math.round(
                suggestion.confidence * 100
              )}%
                                        </span>
                                      </div>
                                      <div class="text-muted smaller">${
                                        suggestion.reasoning || ""
                                      }</div>
                                    </div>`;
            }
          }
        } else {
          html += `<div class="text-muted small mt-2">No suggestions returned</div>`;
        }
      } else {
        html += `<div class="text-danger small mt-2">Error: ${result.error}</div>`;
      }

      html += `</div>`;
    }

    this.showTestResults("results", html);
  }

  /**
   * Display validation test results
   */
  displayValidationResults(results, item) {
    let html = `<h6 class="mt-2 mb-3">Validation Test Results</h6>
                    <div class="small mb-2">Test item: ${item.name}</div>`;

    for (const [description, result] of Object.entries(results)) {
      html += `<div class="result-card mb-3 p-2 border rounded">
                      <div class="d-flex justify-content-between">
                        <strong>Validation Test</strong>
                        <span class="badge ${
                          result.success ? "bg-success" : "bg-danger"
                        }">
                          ${result.success ? "Success" : "Failed"}
                        </span>
                      </div>`;

      if (result.success) {
        html += `<div class="text-muted small">Response time: ${result.responseTime}ms</div>
                         <div class="text-muted small">Issues found: ${result.issueCount}</div>`;

        if (result.data && result.data.length > 0) {
          // Display validation issues
          html += `<div class="mt-2"><strong>Validation Issues:</strong></div>`;

          result.data.forEach((issue) => {
            const severityClass =
              issue.severity === "error" ? "text-danger" : "text-warning";
            const icon = issue.severity === "error" ? "❌" : "⚠️";

            html += `<div class="issue-item mt-1 ${severityClass}">
                                  <div><span class="me-1">${icon}</span> <strong>${
              issue.field
            }:</strong></div>
                                  <div class="small">${issue.message}</div>
                                  <div class="text-muted smaller">
                                    Confidence: ${Math.round(
                                      issue.confidence * 100
                                    )}%
                                  </div>
                                </div>`;
          });
        } else {
          html += `<div class="text-muted small mt-2">No validation issues found</div>`;
        }
      } else {
        html += `<div class="text-danger small mt-2">Error: ${result.error}</div>`;
      }

      html += `</div>`;
    }

    this.showTestResults("results", html);
  }

  /**
   * Update the results display
   */
  showTestResults(type, content) {
    const resultsContainer = document.getElementById("modelTestResults");
    if (!resultsContainer) return;

    if (type === "loading") {
      resultsContainer.innerHTML = `
                <div class="text-center py-3">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="mt-2">${content}</div>
                </div>`;
    } else if (type === "error") {
      resultsContainer.innerHTML = `
                <div class="alert alert-danger mt-3">
                    ${content}
                </div>`;
    } else if (type === "results") {
      resultsContainer.innerHTML = content;
    }
  }
}

// Initialize model tester when document is ready
document.addEventListener("DOMContentLoaded", function () {
  setTimeout(() => {
    const modelTester = new GeminiModelTester();
    modelTester.createUI();
  }, 1500); // Delay to ensure the main app is loaded
});
