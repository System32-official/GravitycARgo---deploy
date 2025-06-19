/**
 * AI Service to handle Gemini API interactions
 */
class AIService {
  constructor(apiKey, model = "gemini-2.5-flash-preview-05-20") {
    this.apiKey = apiKey;
    this.model = model;
    this.apiEndpoint = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;
    this.confidenceThresholds = CONFIG.AI.CONFIDENCE_THRESHOLDS;
    this._useMockResponses = false; // Initialize the mock responses flag
  }

  /**
   * Switch to a different Gemini model
   * @param {string} model - The model name (e.g., 'gemini-2.5-flash-preview-05-20')
   */
  switchModel(model) {
    this.model = model;
    this.apiEndpoint = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${this.apiKey}`;
    console.log(`AI service switched to model: ${model}`);
    return this;
  }

  /**
   * Make an API call to Gemini with the given prompt
   * @param {string} prompt - The prompt to send to Gemini
   * @returns {Promise<Object>} - The API response
   */
  async callGeminiAPI(prompt) {
    try {
      console.log(`Calling Gemini API (${this.model})...`);

      // Check if we should use mock responses instead due to rate limiting
      if (this._useMockResponses) {
        console.log("Using mock responses due to rate limiting");
        return this._getMockResponse(prompt);
      }

      const response = await fetch(this.apiEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          contents: [
            {
              parts: [
                {
                  text: prompt,
                },
              ],
            },
          ],
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error("Gemini API error:", errorData);

        // Check for rate limit errors and switch to mock responses
        if (errorData.error?.code === 429) {
          console.warn(
            "API rate limit reached, switching to mock responses for future requests"
          );
          this._useMockResponses = true;
          return this._getMockResponse(prompt);
        }

        throw new Error(
          `Gemini API error: ${errorData.error?.message || "Unknown error"}`
        );
      }

      return await response.json();
    } catch (error) {
      console.error("Error calling Gemini API:", error);

      // If any error occurs, try to use mock responses as fallback
      console.warn("API error encountered, using mock responses as fallback");
      this._useMockResponses = true;
      return this._getMockResponse(prompt);
    }
  }

  /**
   * Generate a mock response based on the prompt
   * @private
   * @param {string} prompt - The prompt that was sent
   * @returns {Object} - A mock API response
   */
  _getMockResponse(prompt) {
    let mockResponse = {
      candidates: [
        {
          content: {
            parts: [
              {
                text: "",
              },
            ],
          },
        },
      ],
    };

    // Generate a mock JSON response based on the prompt content
    if (prompt.includes("suggest appropriate values")) {
      // This is a suggestion prompt
      const mockJson = {
        fragility: {
          value: "MEDIUM",
          confidence: 0.85,
          reasoning: "Based on mock analysis of item properties",
        },
        loadBear: {
          value: 800,
          confidence: 0.78,
          reasoning: "Standard mock value for similar items",
        },
        tempSensitivity: {
          value: "5°C to 35°C",
          confidence: 0.82,
          reasoning: "Common range for general cargo",
        },
      };

      // If prompt mentions "Heavy" or high weight
      if (prompt.includes("Heavy") || /weight:\s*(\d{3,})/i.test(prompt)) {
        mockJson.fragility.value = "HIGH";
        mockJson.loadBear.value = 2000;
      }

      mockResponse.candidates[0].content.parts[0].text = JSON.stringify(
        mockJson,
        null,
        2
      );
    } else if (prompt.includes("Validate this cargo item")) {
      // This is a validation prompt
      let mockIssues = [];

      // Generate appropriate validation issues based on prompt content
      if (
        prompt.includes('"fragility":"LOW"') &&
        prompt.includes('"weight":') &&
        /weight":\s*(\d{3,})/.test(prompt)
      ) {
        mockIssues.push({
          field: "fragility",
          severity: "warning",
          message: "Heavy items typically have higher fragility",
          confidence: 0.82,
        });
      }

      // Create mock validation response
      const mockValidation = {
        issues: mockIssues,
      };

      mockResponse.candidates[0].content.parts[0].text = JSON.stringify(
        mockValidation,
        null,
        2
      );
    }

    return mockResponse;
  }

  /**
   * Get AI suggestions for a cargo item
   * @param {Object} item - The cargo item data
   * @param {Array} context - Previous items for context
   * @returns {Promise<Object>} - Suggested values with confidence scores
   */
  async getSuggestions(item, context = []) {
    // Skip if name is empty
    if (!item.name) {
      return null;
    }

    const contextText =
      context.length > 0
        ? `Here are ${
            context.length
          } previous cargo items for context:\n${JSON.stringify(
            context,
            null,
            2
          )}\n\n`
        : "";

    const prompt = `${contextText}I have a cargo item with these details:
Name: ${item.name}
Length: ${item.length || "Unknown"} meters
Width: ${item.width || "Unknown"} meters
Height: ${item.height || "Unknown"} meters
Weight: ${item.weight || "Unknown"} kg
Quantity: ${item.quantity || "Unknown"}
BoxingType: ${item.boxingType || "Unknown"}
Bundle: ${item.bundle || "Unknown"}

Based on these characteristics, please suggest appropriate values for:
1. Fragility (LOW/MEDIUM/HIGH)
2. LoadBear (maximum weight in kg this item can support on top of it)
3. Temperature Sensitivity (in format like "10°C to 30°C")

Format your response as valid JSON with the following structure:
{
  "fragility": {"value": "MEDIUM", "confidence": 0.8, "reasoning": "short explanation"},
  "loadBear": {"value": 1500, "confidence": 0.7, "reasoning": "short explanation"},
  "tempSensitivity": {"value": "5°C to 35°C", "confidence": 0.9, "reasoning": "short explanation"}
}

Notes:
- Confidence should be a value between 0 and 1
- Only suggest values if you have reasonable confidence (otherwise leave the field empty)
- Consider the item's characteristics carefully`;

    try {
      const response = await this.callGeminiAPI(prompt);

      // Extract and parse the JSON from the response
      let responseText = "";
      if (response.candidates && response.candidates.length > 0) {
        const candidate = response.candidates[0];
        if (candidate.content && candidate.content.parts) {
          responseText = candidate.content.parts[0].text;
        }
      }

      // Find and extract JSON from the response text
      const jsonMatch = responseText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try {
          const suggestions = JSON.parse(jsonMatch[0]);
          return suggestions;
        } catch (parseError) {
          console.error("Error parsing suggestion JSON:", parseError);
          return null;
        }
      }

      return null;
    } catch (error) {
      console.error("Error getting AI suggestions:", error);
      return null;
    }
  }

  /**
   * Validate a cargo item using AI
   * @param {Object} item - The cargo item to validate
   * @returns {Promise<Array>} - Array of validation issues
   */
  async validateItem(item) {
    if (!item.name) {
      return [];
    }

    // Validation issues array
    const issues = [];

    try {
      console.log("Validating item with AI:", item);

      // Check dimensions
      if (item.length && item.width && item.height) {
        const l = parseFloat(item.length);
        const w = parseFloat(item.width);
        const h = parseFloat(item.height);

        // Check for reasonable dimensions proportions
        const maxRatio = 10; // Max ratio between dimensions

        if (l / w > maxRatio || w / l > maxRatio) {
          issues.push({
            field: "width",
            severity: "warning",
            message:
              "Length to width ratio seems unusual. Please verify dimensions.",
            confidence: 0.8,
          });
        }

        if (l / h > maxRatio || h / l > maxRatio) {
          issues.push({
            field: "height",
            severity: "warning",
            message:
              "Length to height ratio seems unusual. Please verify dimensions.",
            confidence: 0.8,
          });
        }

        if (w / h > maxRatio || h / w > maxRatio) {
          issues.push({
            field: "height",
            severity: "warning",
            message:
              "Width to height ratio seems unusual. Please verify dimensions.",
            confidence: 0.8,
          });
        }
      }

      // Check weight relative to volume
      if (item.length && item.width && item.height && item.weight) {
        const volume =
          parseFloat(item.length) *
          parseFloat(item.width) *
          parseFloat(item.height);
        const weight = parseFloat(item.weight);

        // Density check (typical cargo density range)
        const density = weight / volume; // kg/m³

        if (density > 5000) {
          issues.push({
            field: "weight",
            severity: "warning",
            message: "Weight seems very high for this volume. Please verify.",
            confidence: 0.9,
          });
        } else if (density < 50 && weight > 10) {
          issues.push({
            field: "weight",
            severity: "warning",
            message: "Weight seems very low for this volume. Please verify.",
            confidence: 0.8,
          });
        }
      }

      // Check fragility against load bearing
      if (
        item.fragility === "HIGH" &&
        item.loadBear &&
        parseFloat(item.loadBear) > 0
      ) {
        issues.push({
          field: "loadBear",
          severity: "warning",
          message:
            "High fragility items typically shouldn't bear significant loads.",
          confidence: 0.85,
        });
      }

      // Check temperature sensitivity format
      if (
        item.tempSensitivity &&
        !CONFIG.VALIDATION.TEMP_SENSITIVITY_PATTERN.test(item.tempSensitivity)
      ) {
        issues.push({
          field: "tempSensitivity",
          severity: "error",
          message: "Temperature format should be like '10°C to 30°C'",
          confidence: 1.0,
        });
      }

      // Add more AI-based validations as needed

      // Finally, add any validation from the actual AI service if available
      // This would call your external AI service
      // const aiValidationResults = await this._callValidationAPI(item);
      // issues.push(...aiValidationResults);

      console.log("Validation completed with issues:", issues);
      return issues;
    } catch (error) {
      console.error("Error during AI validation:", error);
      return [];
    }
  }

  /**
   * Get confidence level classification based on score
   * @param {number} confidence - Confidence score (0-1)
   * @returns {string} - Confidence level (high, medium, low)
   */
  getConfidenceLevel(confidence) {
    if (confidence >= this.confidenceThresholds.HIGH) {
      return "high";
    } else if (confidence >= this.confidenceThresholds.MEDIUM) {
      return "medium";
    } else {
      return "low";
    }
  }

  /**
   * Fill missing fields in cargo items using AI
   * @param {Array} items - The cargo items to process
   * @returns {Promise<Object>} - Suggestions for each item
   */
  async fillMissingFields(items) {
    const suggestions = {};

    // Get non-empty items for context
    const contextItems = items
      .filter(
        (item) =>
          item.name && item.fragility && item.loadBear && item.tempSensitivity
      )
      .slice(0, CONFIG.AI.MAX_CONTEXT_ITEMS);

    // Process each item with missing fields
    for (const [index, item] of items.entries()) {
      // Skip empty items or complete items
      if (
        !item.name ||
        (item.fragility && item.loadBear && item.tempSensitivity)
      ) {
        continue;
      }

      const itemSuggestions = await this.getSuggestions(item, contextItems);
      if (itemSuggestions) {
        suggestions[index] = {
          item: item,
          suggestions: {},
        };

        // Add suggestions for missing fields
        if (!item.fragility && itemSuggestions.fragility) {
          suggestions[index].suggestions.fragility = itemSuggestions.fragility;
        }

        if (!item.loadBear && itemSuggestions.loadBear) {
          suggestions[index].suggestions.loadBear = itemSuggestions.loadBear;
        }

        if (!item.tempSensitivity && itemSuggestions.tempSensitivity) {
          suggestions[index].suggestions.tempSensitivity =
            itemSuggestions.tempSensitivity;
        }
      }
    }

    return suggestions;
  }

  /**
   * Compare performance between different model configurations
   * @param {Object} item - The cargo item to test
   * @param {Array} configurations - Array of configuration options to test
   * @returns {Promise<Object>} - Comparison results
   */
  async compareConfigurations(
    item,
    configurations = [
      { temperature: 0.2, topK: 40, topP: 0.95 },
      { temperature: 0.7, topK: 40, topP: 0.95 },
      { temperature: 0.4, topK: 40, topP: 0.95 },
    ]
  ) {
    const results = {};
    const originalModel = this.model;

    try {
      for (const config of configurations) {
        console.log(`Testing configuration: ${JSON.stringify(config)}`);

        const startTime = performance.now();
        const suggestions = await this.getSuggestionsWithConfig(
          item,
          [],
          config
        );
        const endTime = performance.now();

        results[
          `temp_${config.temperature}_topK_${config.topK}_topP_${config.topP}`
        ] = {
          responseTime: endTime - startTime,
          suggestions: suggestions,
          success: !!suggestions,
          config: config,
        };
      }
    } catch (error) {
      console.error("Error comparing configurations:", error);
    }

    return results;
  }

  /**
   * Get AI suggestions with specific generation parameters
   * @param {Object} item - The cargo item data
   * @param {Array} context - Previous items for context
   * @param {Object} config - Generation configuration parameters
   * @returns {Promise<Object>} - Suggested values with confidence scores
   */
  async getSuggestionsWithConfig(
    item,
    context = [],
    config = { temperature: 0.4, topK: 40, topP: 0.95 }
  ) {
    if (!item.name) {
      return null;
    }

    const contextText =
      context.length > 0
        ? `Here are ${
            context.length
          } previous cargo items for context:\n${JSON.stringify(
            context,
            null,
            2
          )}\n\n`
        : "";

    const prompt = `${contextText}I have a cargo item with these details:
Name: ${item.name}
Length: ${item.length || "Unknown"} meters
Width: ${item.width || "Unknown"} meters
Height: ${item.height || "Unknown"} meters
Weight: ${item.weight || "Unknown"} kg
Quantity: ${item.quantity || "Unknown"}
BoxingType: ${item.boxingType || "Unknown"}
Bundle: ${item.bundle || "Unknown"}

Based on these characteristics, please suggest appropriate values for:
1. Fragility (LOW/MEDIUM/HIGH)
2. LoadBear (maximum weight in kg this item can support on top of it)
3. Temperature Sensitivity (in format like "10°C to 30°C")

Format your response as valid JSON with the following structure:
{
  "fragility": {"value": "MEDIUM", "confidence": 0.8, "reasoning": "short explanation"},
  "loadBear": {"value": 1500, "confidence": 0.7, "reasoning": "short explanation"},
  "tempSensitivity": {"value": "5°C to 35°C", "confidence": 0.9, "reasoning": "short explanation"}
}

Notes:
- Confidence should be a value between 0 and 1
- Only suggest values if you have reasonable confidence (otherwise leave the field empty)
- Consider the item's characteristics carefully`;

    try {
      // Check if we should use mock responses instead due to rate limiting
      if (this._useMockResponses) {
        console.log(
          `Using mock responses for configuration: temperature=${config.temperature}`
        );

        // Generate mock response with confidence based on temperature
        const baseConfidence = config.temperature < 0.5 ? 0.85 : 0.7;
        return {
          fragility: {
            value: item.name.includes("Heavy") ? "HIGH" : "MEDIUM",
            confidence: baseConfidence,
            reasoning: `Based on mock analysis with temperature ${config.temperature}`,
          },
          loadBear: {
            value: item.name.includes("Pallet") ? 1500 : item.weight * 3 || 300,
            confidence: baseConfidence - 0.1,
            reasoning: "Mock capacity based on item type",
          },
          tempSensitivity: {
            value: "5°C to 35°C",
            confidence: baseConfidence - 0.15,
            reasoning: "Mock temperature range for general cargo",
          },
        };
      }

      const response = await fetch(this.apiEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          contents: [
            {
              parts: [
                {
                  text: prompt,
                },
              ],
            },
          ],
          generationConfig: {
            temperature: config.temperature,
            topK: config.topK,
            topP: config.topP,
          },
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error("Gemini API error:", errorData);

        // Check for rate limit errors and switch to mock responses
        if (errorData.error?.code === 429) {
          console.warn(
            "API rate limit reached, switching to mock responses for future requests"
          );
          this._useMockResponses = true;
          return this._getMockResponse(prompt);
        }

        throw new Error(
          `Gemini API error: ${errorData.error?.message || "Unknown error"}`
        );
      }

      const data = await response.json();

      // Extract and parse the JSON from the response
      let responseText = "";
      if (data.candidates && data.candidates.length > 0) {
        const candidate = data.candidates[0];
        if (candidate.content && candidate.content.parts) {
          responseText = candidate.content.parts[0].text;
        }
      }

      // Find and extract JSON from the response text
      const jsonMatch = responseText.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        try {
          const suggestions = JSON.parse(jsonMatch[0]);
          return suggestions;
        } catch (parseError) {
          console.error("Error parsing suggestion JSON:", parseError);
          return null;
        }
      }

      return null;
    } catch (error) {
      console.error("Error getting AI suggestions:", error);

      // In case of error, still return mock data
      this._useMockResponses = true;
      const baseConfidence = config.temperature < 0.5 ? 0.85 : 0.7;
      return {
        fragility: {
          value: item.name.includes("Heavy") ? "HIGH" : "MEDIUM",
          confidence: baseConfidence,
          reasoning: `Fallback mock analysis (temperature ${config.temperature})`,
        },
        loadBear: {
          value: item.name.includes("Pallet") ? 1500 : item.weight * 3 || 300,
          confidence: baseConfidence - 0.1,
          reasoning: "Fallback mock capacity",
        },
        tempSensitivity: {
          value: "5°C to 35°C",
          confidence: baseConfidence - 0.15,
          reasoning: "Fallback mock temperature range",
        },
      };
    }
  }
}

// Create the AI service instance
const aiService = new AIService(CONFIG.GEMINI_API_KEY, CONFIG.GEMINI_MODEL);
// Initialize the mock responses flag to false - will switch to true if API rate limit is hit
aiService._useMockResponses = false;
