/**
 * GravityCARgo - UI Animation and Interaction Module
 * Handles animations, transitions, theme switching, and UI effects
 */

// Wait for DOM content to be loaded
document.addEventListener("DOMContentLoaded", function () {
  // Initialize AOS (Animate On Scroll)
  AOS.init({
    duration: 800,
    easing: "ease-in-out",
    once: true,
    mirror: false,
    disable: "mobile",
  });

  // Initialize components
  initializePreloader();
  initializeCustomCursor();
  initializeThemeToggle();
  initializeMapControls();
  initializeCheckpointNavigation();
  initializeHelpModal();
  initializeToasts();

  // Setup calc button effects
  setupButtonEffects();
});

/**
 * Preloader Animation
 * Handles the loading animation and transitions it out
 */
function initializePreloader() {
  const preloader = document.querySelector(".preloader");
  if (!preloader) return;

  // Fade out preloader after content loads
  window.addEventListener("load", () => {
    gsap.to(preloader, {
      opacity: 0,
      duration: 0.8,
      ease: "power3.inOut",
      onComplete: () => {
        preloader.style.display = "none";

        // Animate main content entrance
        gsap.from(".app-heading", {
          y: 30,
          opacity: 0,
          duration: 0.8,
          ease: "back.out(1.4)",
          delay: 0.3,
        });
      },
    });
  });
}

/**
 * Custom Cursor Implementation
 * Replaces default cursor with custom animated cursor
 */
function initializeCustomCursor() {
  const cursorDot = document.querySelector(".cursor-dot");
  const cursorOutline = document.querySelector(".cursor-outline");

  // Check if cursor elements exist
  if (!cursorDot || !cursorOutline) return;

  // Only enable custom cursor on non-touch devices
  if (!("ontouchstart" in window)) {
    document.body.classList.add("cursor-enabled");

    // Function to update cursor position
    const updateCursorPosition = (e) => {
      gsap.to(cursorDot, {
        x: e.clientX,
        y: e.clientY,
        duration: 0.1,
        ease: "power2.out",
      });

      gsap.to(cursorOutline, {
        x: e.clientX,
        y: e.clientY,
        duration: 0.5,
        ease: "power2.out",
      });
    };

    // Function to handle cursor over interactive elements
    const handleCursorHover = () => {
      gsap.to(cursorOutline, {
        scale: 1.5,
        duration: 0.3,
        ease: "power2.out",
      });
    };

    // Function to handle cursor leaving interactive elements
    const handleCursorLeave = () => {
      gsap.to(cursorOutline, {
        scale: 1,
        duration: 0.3,
        ease: "power2.out",
      });
    };

    // Add event listeners
    document.addEventListener("mousemove", updateCursorPosition);

    // Add hover effect to all interactive elements
    const interactiveElements = document.querySelectorAll(
      "a, button, input, select, .interactive"
    );
    interactiveElements.forEach((element) => {
      element.addEventListener("mouseenter", handleCursorHover);
      element.addEventListener("mouseleave", handleCursorLeave);
    });
  }
}

/**
 * Theme Toggle Functionality
 * Switches between light and dark theme modes
 */
function initializeThemeToggle() {
  const themeToggle = document.getElementById("theme-switch");
  if (!themeToggle) return;

  // Check for saved theme preference or set default
  const savedTheme = localStorage.getItem("theme") || "light";
  document.documentElement.className = `${savedTheme}-mode`;

  // Toggle theme on click
  themeToggle.addEventListener("click", () => {
    // Toggle theme class
    const isLightMode =
      document.documentElement.classList.contains("light-mode");
    const newTheme = isLightMode ? "dark" : "light";

    // Animate transition
    gsap.to("html", {
      opacity: 0.8,
      duration: 0.2,
      onComplete: () => {
        document.documentElement.className = `${newTheme}-mode`;
        localStorage.setItem("theme", newTheme);

        gsap.to("html", {
          opacity: 1,
          duration: 0.2,
        });
      },
    });
  });
}

/**
 * Map Controls
 * Adds functionality to map control buttons
 */
function initializeMapControls() {
  const zoomInBtn = document.getElementById("zoom-in");
  const zoomOutBtn = document.getElementById("zoom-out");
  const recenterBtn = document.getElementById("recenter");

  if (!zoomInBtn || !zoomOutBtn || !recenterBtn) return;

  // Set up click animations
  [zoomInBtn, zoomOutBtn, recenterBtn].forEach((btn) => {
    btn.addEventListener("click", function () {
      gsap.to(this, {
        scale: 0.9,
        duration: 0.1,
        onComplete: () => {
          gsap.to(this, {
            scale: 1,
            duration: 0.1,
          });
        },
      });
    });
  });

  // Add click handlers - these will be connected to the map in main.js
  zoomInBtn.addEventListener("click", function () {
    if (window.mapState && window.mapState.map) {
      window.mapState.map.zoomIn();
    }
  });

  zoomOutBtn.addEventListener("click", function () {
    if (window.mapState && window.mapState.map) {
      window.mapState.map.zoomOut();
    }
  });

  recenterBtn.addEventListener("click", function () {
    if (window.mapState && window.mapState.map && window.mapState.mainRoute) {
      window.mapState.map.fitBounds(window.mapState.mainRoute.getBounds());
    }
  });
}

/**
 * Checkpoint Navigation
 * Implements navigation between checkpoints
 */
function initializeCheckpointNavigation() {
  const prevBtn = document.getElementById("prev-checkpoint");
  const nextBtn = document.getElementById("next-checkpoint");
  const counter = document.getElementById("checkpoint-counter");

  if (!prevBtn || !nextBtn || !counter) return;

  // This will be populated from main.js after route calculation
  window.checkpointNavigator = {
    currentIndex: 0,
    totalCheckpoints: 0,

    initialize: function (totalCheckpoints) {
      this.currentIndex = 0;
      this.totalCheckpoints = totalCheckpoints;
      this.updateUI();

      // Enable buttons if we have checkpoints
      prevBtn.disabled = true;
      nextBtn.disabled = totalCheckpoints <= 1;

      // Update counter
      counter.textContent = `${this.totalCheckpoints} checkpoints`;
    },

    previous: function () {
      if (this.currentIndex > 0) {
        this.currentIndex--;
        this.updateUI();
        this.scrollToCurrentCheckpoint();
      }
    },

    next: function () {
      if (this.currentIndex < this.totalCheckpoints - 1) {
        this.currentIndex++;
        this.updateUI();
        this.scrollToCurrentCheckpoint();
      }
    },

    updateUI: function () {
      // Update button states
      prevBtn.disabled = this.currentIndex === 0;
      nextBtn.disabled = this.currentIndex >= this.totalCheckpoints - 1;

      // Update counter display
      counter.textContent = `${this.currentIndex + 1} / ${
        this.totalCheckpoints
      }`;

      // Highlight current checkpoint on map (will be implemented in main.js)
      if (window.focusCheckpoint) {
        window.focusCheckpoint(this.currentIndex);
      }
    },

    scrollToCurrentCheckpoint: function () {
      const allCheckpoints = document.querySelectorAll(".checkpoint-card");
      if (allCheckpoints.length > this.currentIndex) {
        const checkpoint = allCheckpoints[this.currentIndex];

        // Smooth scroll to this checkpoint
        checkpoint.scrollIntoView({ behavior: "smooth", block: "center" });

        // Highlight the current checkpoint with animation
        gsap.fromTo(
          checkpoint,
          {
            boxShadow:
              "0 0 0 3px rgba(66, 99, 235, 0.7), 0 3px 10px rgba(0, 0, 0, 0.08)",
          },
          {
            boxShadow: "0 3px 10px rgba(0, 0, 0, 0.08)",
            duration: 2,
            ease: "power2.out",
          }
        );
      }
    },
  };

  // Add event listeners
  prevBtn.addEventListener("click", () =>
    window.checkpointNavigator.previous()
  );
  nextBtn.addEventListener("click", () => window.checkpointNavigator.next());
}

/**
 * Modal Handling
 * Sets up the help modal
 */
function initializeHelpModal() {
  const helpBtn = document.querySelector(".help-btn");
  const helpModal = document.getElementById("help-modal");
  const closeModal = document.querySelector(".close-modal");

  if (!helpBtn || !helpModal || !closeModal) return;

  helpBtn.addEventListener("click", () => {
    // Show modal with animation
    helpModal.style.display = "flex";
    gsap.fromTo(
      helpModal,
      { opacity: 0 },
      { opacity: 1, duration: 0.3, ease: "power2.inOut" }
    );

    const modalContainer = helpModal.querySelector(".modal-container");
    gsap.fromTo(
      modalContainer,
      { y: 30, opacity: 0 },
      { y: 0, opacity: 1, duration: 0.4, delay: 0.1, ease: "back.out(1.7)" }
    );
  });

  closeModal.addEventListener("click", () => {
    // Hide modal with animation
    gsap.to(helpModal, {
      opacity: 0,
      duration: 0.3,
      ease: "power2.inOut",
      onComplete: () => (helpModal.style.display = "none"),
    });
  });

  // Close on click outside
  helpModal.addEventListener("click", (e) => {
    if (e.target === helpModal) {
      gsap.to(helpModal, {
        opacity: 0,
        duration: 0.3,
        ease: "power2.inOut",
        onComplete: () => (helpModal.style.display = "none"),
      });
    }
  });
}

/**
 * Toast Notification System
 * Creates toast notifications for user feedback
 */
function initializeToasts() {
  const toastContainer = document.querySelector(".toast-container");
  if (!toastContainer) return;

  window.showToast = function (message, type = "info", duration = 3000) {
    // Create toast element
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    // Set icon based on type
    let icon;
    switch (type) {
      case "success":
        icon = "check-circle-fill";
        break;
      case "error":
        icon = "exclamation-circle-fill";
        break;
      case "warning":
        icon = "exclamation-triangle-fill";
        break;
      default:
        icon = "info-circle-fill";
    }

    // Set content
    toast.innerHTML = `
      <div class="toast-content">
        <i class="bi bi-${icon}"></i>
        <span>${message}</span>
      </div>
      <button class="toast-close"><i class="bi bi-x"></i></button>
    `;

    // Append to container
    toastContainer.appendChild(toast);

    // Animate in
    gsap.fromTo(
      toast,
      { x: 50, opacity: 0 },
      { x: 0, opacity: 1, duration: 0.3, ease: "power2.out" }
    );

    // Set up close button
    const closeBtn = toast.querySelector(".toast-close");
    closeBtn.addEventListener("click", () => {
      closeToast(toast);
    });

    // Auto-close after duration
    const timeoutId = setTimeout(() => {
      closeToast(toast);
    }, duration);

    // Store timeout ID on element
    toast.dataset.timeoutId = timeoutId;

    // Function to close toast
    function closeToast(toastElement) {
      // Clear the timeout
      clearTimeout(parseInt(toastElement.dataset.timeoutId));

      // Animate out and remove
      gsap.to(toastElement, {
        x: 50,
        opacity: 0,
        duration: 0.3,
        ease: "power2.in",
        onComplete: () => {
          toastContainer.removeChild(toastElement);
        },
      });
    }
  };
}

/**
 * Button Effects
 * Add animations and loading states to buttons
 */
function setupButtonEffects() {
  const calcBtn = document.querySelector(".calc-btn");
  if (!calcBtn) return;

  // Original click handler
  const originalClickHandler = calcBtn.onclick;

  // Set up new click handler with animation
  calcBtn.onclick = async function (event) {
    // Show loading state
    calcBtn.classList.add("loading");

    // Get button content
    const btnContent = calcBtn.querySelector(".btn-content");
    const btnLoading = calcBtn.querySelector(".btn-loading");

    if (btnContent && btnLoading) {
      btnContent.style.display = "none";
      btnLoading.style.display = "flex";
    }

    try {
      // Call original handler if it exists
      if (originalClickHandler) {
        await originalClickHandler.call(this, event);
      }
    } finally {
      // Restore button state after a short delay for UX
      setTimeout(() => {
        calcBtn.classList.remove("loading");

        if (btnContent && btnLoading) {
          btnContent.style.display = "flex";
          btnLoading.style.display = "none";
        }
      }, 500); // Delay to avoid flickering if response is too fast
    }
  };

  // Add hover effects to all action buttons
  document
    .querySelectorAll(".action-btn, .geo-btn, .remove-btn")
    .forEach((btn) => {
      btn.addEventListener("mouseenter", () => {
        gsap.to(btn, {
          y: -2,
          boxShadow: "0 4px 8px rgba(0, 0, 0, 0.1)",
          duration: 0.2,
        });
      });

      btn.addEventListener("mouseleave", () => {
        gsap.to(btn, {
          y: 0,
          boxShadow: "0 2px 5px rgba(0, 0, 0, 0.05)",
          duration: 0.2,
        });
      });
    });
}
