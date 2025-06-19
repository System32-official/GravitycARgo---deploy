const CONFIG = {
  // Gemini API config
  GEMINI_API_KEY: "AIzaSyB0tRWaZXYa-fC-_dAHBBvRTQkiMolpukI",
  GEMINI_MODEL: "gemini-2.5-flash-preview-05-20",
  GEMINI_MODELS: [
    {
      id: "gemini-2.5-flash-preview-05-20",
      name: "Gemini 2.5 Flash Preview",
      default: true,
    },
  ],

  // Table configuration
  TABLE_COLUMNS: [
    {
      data: "name",
      title: "Name",
      width: 150,
      required: true,
    },
    {
      data: "length",
      title: "Length (m)",
      type: "numeric",
      width: 120,
      required: true,
      format: "0.00",
      tooltip: "Enter length in meters",
    },
    {
      data: "width",
      title: "Width (m)",
      type: "numeric",
      width: 120,
      required: true,
      format: "0.00",
      tooltip: "Enter width in meters",
    },
    {
      data: "height",
      title: "Height (m)",
      type: "numeric",
      width: 120,
      required: true,
      format: "0.00",
      tooltip: "Enter height in meters",
    },
    {
      data: "weight",
      title: "Weight (kg)",
      type: "numeric",
      width: 120,
      required: true,
      format: "0.00",
      tooltip: "Enter weight in kilograms",
    },
    {
      data: "quantity",
      title: "Quantity",
      type: "numeric",
      width: 100,
      required: true,
      format: "0",
      tooltip: "Enter number of items",
    },
    {
      data: "fragility",
      title: "Fragility",
      type: "dropdown",
      width: 120,
      required: true,
      source: ["LOW", "MEDIUM", "HIGH"],
      tooltip: "Select item fragility",
      aiAssisted: true,
      icon: "📦",
    },
    {
      data: "loadBear",
      title: "LoadBear (kg)",
      type: "numeric",
      width: 130,
      required: true,
      format: "0.00",
      tooltip: "Maximum weight this item can support",
      aiAssisted: true,
    },
    {
      data: "boxingType",
      title: "BoxingType",
      type: "dropdown",
      width: 130,
      required: true,
      source: ["BOX", "PALLET", "LOOSE", "CONTAINER", "CRATE"],
      tooltip: "Select packaging type",
    },
    {
      data: "bundle",
      title: "Bundle",
      type: "dropdown",
      width: 120,
      required: true,
      source: ["YES", "NO"],
      tooltip: "Can this item be bundled?",
    },
    {
      data: "tempSensitivity",
      title: "Temperature Sensitivity",
      width: 170,
      required: true,
      tooltip: "Format: 10°C to 30°C",
      aiAssisted: true,
      icon: "🧊",
    },
  ],

  // LocalStorage keys
  STORAGE_KEYS: {
    CARGO_DATA: "gravitycargo-data",
    THEME: "gravitycargo-theme",
    LAST_EXPORT: "gravitycargo-last-export",
  },

  // Default values for new rows
  DEFAULT_ROW: {
    name: "",
    length: null,
    width: null,
    height: null,
    weight: null,
    quantity: "", // Changed from 1 to empty string
    fragility: "", // Changed from "LOW" to empty string
    loadBear: null,
    boxingType: "", // Changed from "BOX" to empty string
    bundle: "", // Changed from "NO" to empty string
    tempSensitivity: "",
  },

  // Validation patterns
  VALIDATION: {
    TEMP_SENSITIVITY_PATTERN: /^-?\d+°C to -?\d+°C$/,
    MIN_DIMENSIONS: 0.01,
    MAX_DIMENSIONS: 50,
    MIN_WEIGHT: 0.1,
    MAX_WEIGHT: 40000,
    MIN_QUANTITY: 1,
    MAX_QUANTITY: 10000,
    MIN_LOADBEAR: 0,
    MAX_LOADBEAR: 100000,
  },

  // Notification settings
  NOTIFICATIONS: {
    AUTO_DISMISS_TIME: 5000,
    POSITION: "top-end",
  },

  // AI config
  AI: {
    MAX_CONTEXT_ITEMS: 10, // Number of previous items to use as context
    CONFIDENCE_THRESHOLDS: {
      HIGH: 0.85,
      MEDIUM: 0.5,
      LOW: 0,
    },
  },
};
