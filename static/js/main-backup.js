// Backup of original main.js content
// Transport mode mapping
const transportModeMapping = {
  "1": "Road Transport",
  "2": "Sea Transport", 
  "3": "Air Transport",
  "4": "Rail Transport",
  "5": "Custom",
};

// Prevent conflicts with index.html inline scripts
if (window.location.pathname === '/') {
  console.log("Main.js: Skipping initialization on index page to prevent conflicts");
} else {
  document.addEventListener("DOMContentLoaded", function () {
    console.log("Main.js loaded successfully for non-index pages");
    // Main.js functionality for other pages can go here
  });
}
