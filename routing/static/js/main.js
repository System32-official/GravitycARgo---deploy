// Make these functions globally available
window.getCurrentLocation = null;
window.calculateRoute = null;
window.switchToRoute = null;

// Global state object - single declaration
const mapState = {
  map: null,
  mainRoute: null,
  alternativeRoutes: [],
  markers: [],
  tempMarker: null,
  currentCheckpoints: [],
  currentRoute: null,
};

// Wait for jQuery to be loaded
(function (factory) {
  if (typeof jQuery === "undefined") {
    console.error("jQuery is required");
    return;
  }
  factory(jQuery);
})(function ($) {
  "use strict";

  // Initialize map
  function initMap() {
    if (!mapState.map) {
      mapState.map = L.map("map").setView([20, 0], 2);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(
        mapState.map
      );

      // Add click handler
      mapState.map.on("click", function (e) {
        const activeInput = $(".location-input-active");
        if (activeInput.length) {
          const { lat, lng } = e.latlng;
          activeInput.val(`${lat.toFixed(6)}, ${lng.toFixed(6)}`);

          if (mapState.tempMarker) {
            mapState.map.removeLayer(mapState.tempMarker);
          }
          mapState.tempMarker = L.marker([lat, lng])
            .bindPopup(
              activeInput.attr("id") === "source" ? "Source" : "Destination"
            )
            .addTo(mapState.map);
        }
      });
    }
  }

  // Assign functions to window object to make them globally accessible
  window.getCurrentLocation = function () {
    if (navigator.geolocation) {
      // Add loading indicator to button instead of select element
      const button = document.querySelector(
        'button[onclick="getCurrentLocation()"]'
      );
      button.classList.add("loading");
      button.disabled = true;

      navigator.geolocation.getCurrentPosition(
        async (position) => {
          const { latitude, longitude } = position.coords;

          try {
            // Ensure the map is initialized
            if (!mapState.map) {
              initMap();
            }

            // Reverse geocode the coordinates to get location name
            const response = await fetch(
              `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json`,
              {
                headers: { "User-Agent": "GravityCARgo Route Planner" },
              }
            );
            const data = await response.json();

            // Create the location data
            const locationData = {
              id: `${latitude},${longitude}`,
              text:
                data.display_name ||
                `Location at ${latitude.toFixed(6)}, ${longitude.toFixed(6)}`,
              lat: latitude,
              lng: longitude,
            };

            // Create or update the option in the select
            let option = new Option(
              locationData.text,
              locationData.id,
              true,
              true
            );

            // Remove any existing options first except the placeholder
            $("#source option").not('[value=""]').remove();

            // Append new option and select it
            $("#source").append(option).val(locationData.id).trigger("change");

            // Update map view
            mapState.map.setView([latitude, longitude], 13);

            // Clear existing markers and add new one
            clearMap();
            const marker = L.marker([latitude, longitude], {
              draggable: true,
            })
              .bindPopup("Your Current Location")
              .addTo(mapState.map);

            // Update coordinates when marker is dragged
            marker.on("dragend", function (e) {
              const pos = e.target.getLatLng();
              const newData = {
                id: `${pos.lat},${pos.lng}`,
                text: `Location at ${pos.lat.toFixed(6)}, ${pos.lng.toFixed(
                  6
                )}`,
                lat: pos.lat,
                lng: pos.lng,
              };

              // Update the select2 with new position data
              let newOption = new Option(newData.text, newData.id, true, true);
              $("#source")
                .empty()
                .append(newOption)
                .val(newData.id)
                .trigger("change");
            });

            mapState.markers.push(marker);
            console.log("Current location set successfully:", locationData);
          } catch (error) {
            console.error("Error setting location:", error);
            alert("Error setting location: " + error.message);
          } finally {
            // Remove loading indicator from button
            button.classList.remove("loading");
            button.disabled = false;
          }
        },
        (error) => {
          console.error("Geolocation error:", error);
          button.classList.remove("loading");
          button.disabled = false;

          let errorMsg = "Error getting your location";
          switch (error.code) {
            case error.PERMISSION_DENIED:
              errorMsg =
                "Location access denied. Please allow location access in your browser settings.";
              break;
            case error.POSITION_UNAVAILABLE:
              errorMsg =
                "Location information is unavailable. Please try again later.";
              break;
            case error.TIMEOUT:
              errorMsg = "Location request timed out. Please try again.";
              break;
          }
          alert(errorMsg);
        },
        {
          enableHighAccuracy: true,
          timeout: 10000, // Extended timeout
          maximumAge: 0,
        }
      );
    } else {
      alert("Geolocation is not supported by your browser");
    }
  };

  // Add input focus handlers
  function setupLocationInputs() {
    // Update to handle multiple destinations
    const handleLocationInputFocus = (input) => {
      // Remove active class from all inputs
      document
        .querySelectorAll(".location-input-active")
        .forEach((el) => el.classList.remove("location-input-active"));
      // Add active class to current input
      input.classList.add("location-input-active");
    };

    // Set up source input
    const sourceInput = document.getElementById("source");
    if (sourceInput) {
      sourceInput.addEventListener("focus", () =>
        handleLocationInputFocus(sourceInput)
      );
      sourceInput.addEventListener("blur", () => {
        setTimeout(() => {
          sourceInput.classList.remove("location-input-active");
        }, 200);
      });
    }

    // Set up destination inputs (including dynamically added ones)
    $(document).on("focus", ".destination", function () {
      handleLocationInputFocus(this);
    });
    $(document).on("blur", ".destination", function () {
      const input = this;
      setTimeout(() => {
        input.classList.remove("location-input-active");
      }, 200);
    });
  }

  // Handle adding and removing destinations
  function setupDestinationControls() {
    // Add destination button
    $("#add-destination").click(function () {
      const destinationEntries = $(".destination-entry");
      const newIndex = destinationEntries.length + 1;

      const newDestinationHtml = `
        <div class="mb-3 destination-entry">
          <label class="form-label">Destination ${newIndex}</label>
          <div class="input-group">
            <select class="form-control location-select destination" data-index="${newIndex}">
              <option value="">Type to search location...</option>
            </select>
            <button class="btn btn-outline-danger remove-destination" type="button">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </div>
      `;

      $("#destinations-container").append(newDestinationHtml);

      // Initialize the newly added select2
      $(".destination[data-index='" + newIndex + "']").select2({
        ajax: {
          url: "/search_location",
          dataType: "json",
          delay: 250,
          data: function (params) {
            return {
              q: params.term,
            };
          },
          processResults: function (data) {
            return {
              results: data.locations.map((loc) => ({
                id: `${loc.lat},${loc.lon}`,
                text: loc.display_name,
              })),
            };
          },
          cache: true,
        },
        minimumInputLength: 3,
        placeholder: "Type to search location...",
      });

      // Show all remove buttons
      $(".remove-destination").show();
    });

    // Remove destination button
    $(document).on("click", ".remove-destination", function () {
      $(this).closest(".destination-entry").remove();

      // Renumber the remaining destinations
      $(".destination-entry").each(function (index) {
        $(this)
          .find("label")
          .text(`Destination ${index + 1}`);
        $(this)
          .find(".destination")
          .attr("data-index", index + 1);
      });

      // If only one destination remains, hide its remove button
      if ($(".destination-entry").length === 1) {
        $(".remove-destination").hide();
      }
    });
  }

  // Initialize location selects with Select2
  function initializeLocationSelects() {
    $(".location-select").select2({
      ajax: {
        url: "/search_location",
        dataType: "json",
        delay: 250,
        data: function (params) {
          return {
            q: params.term,
          };
        },
        processResults: function (data) {
          return {
            results: data.locations.map((loc) => ({
              id: `${loc.lat},${loc.lon}`,
              text: loc.display_name,
            })),
          };
        },
        cache: true,
      },
      minimumInputLength: 3,
      placeholder: "Type to search location...",
    });

    // Handle optimal checkpoints toggle
    $("#optimal-checkpoints").change(function () {
      const checkpointsInput = $("#checkpoints");
      checkpointsInput.prop("disabled", this.checked);
    });
  }

  // Show loading indicator
  function showLoading() {
    document.getElementById("map-loading").style.display = "flex";
  }

  // Hide loading indicator
  function hideLoading() {
    document.getElementById("map-loading").style.display = "none";
  }

  // Assign functions to window object to make them globally accessible
  window.calculateRoute = async function () {
    try {
      // Show loading indicator
      showLoading();

      const source = $("#source").select2("data")[0];

      // Get all destinations
      const destinations = [];
      $(".destination").each(function () {
        const destData = $(this).select2("data")[0];
        if (destData) {
          destinations.push(destData);
        }
      });

      const startTime = $("#start-time").val();

      if (!source || destinations.length === 0 || !startTime) {
        alert("Please select source, at least one destination and start time");
        return;
      }

      // Parse source coordinates
      const sourceCoords = source.id.split(",").map(Number);

      // Parse destination coordinates
      const destinationCoordinates = destinations.map((dest) => ({
        name: dest.text,
        coords: dest.id.split(",").map(Number),
      }));

      const useOptimal = $("#optimal-checkpoints").is(":checked");
      const checkpoints = useOptimal ? null : parseInt($("#checkpoints").val());

      const response = await fetch("/calculate_route", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source: source.text,
          source_coords: sourceCoords,
          destinations: destinationCoordinates,
          checkpoints: checkpoints,
          start_time: startTime,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      if (data.status === "success") {
        clearMap();
        mapState.currentRoute = data.main_route;
        mapState.currentCheckpoints = data.checkpoints;
        displayRoute(
          data.main_route,
          data.alternative_routes,
          data.checkpoints
        );
        displayRouteInfo(data);
        displayCheckpoints(data.checkpoints);
        displayAlternativeRoutes(data.alternative_routes);
      } else {
        alert("Error: " + data.message);
      }

      // When complete, hide loading
      hideLoading();
    } catch (error) {
      hideLoading();
      alert("Error calculating route: " + error);
    }
  };

  // Modified display functions to use mapState
  function displayRoute(mainRoute, alternatives, checkpoints) {
    // Main route
    mapState.mainRoute = L.polyline(decodePolyline(mainRoute.geometry), {
      color: "#007bff",
      weight: 5,
    }).addTo(mapState.map);

    // Alternative routes
    alternatives.forEach((route, index) => {
      const altPath = L.polyline(decodePolyline(route.geometry), {
        color: "#28a745",
        weight: 3,
        opacity: 0.6,
        dashArray: "10, 10",
      }).addTo(mapState.map);
      mapState.alternativeRoutes.push(altPath);
    });

    // Checkpoints
    checkpoints.forEach((point, index) => {
      const marker = L.marker(point.coords)
        .bindPopup(
          `<b>${point.name}</b><br/>Lat: ${point.coords[0]}<br/>Lon: ${point.coords[1]}`
        )
        .addTo(mapState.map);
      mapState.markers.push(marker);
    });

    // Fit bounds
    mapState.map.fitBounds(mapState.mainRoute.getBounds(), {
      padding: [50, 50],
    });
  }

  // Add function to display alternative routes
  function displayAlternativeRoutes(alternatives) {
    const altRoutesDiv = document.getElementById("alternativeRoutes");
    if (!altRoutesDiv || !alternatives.length) return;

    const html = `
            <h6 class="mt-3">Alternative Routes</h6>
            ${alternatives
              .map(
                (route, index) => `
                    <div class="alternative-route" onclick="switchToRoute(${index})">
                        <strong>Route ${index + 1}</strong>
                        <div>Distance: ${(route.distance / 1000).toFixed(
                          2
                        )} km</div>
                        <div>Duration: ${(route.duration / 3600).toFixed(
                          2
                        )} hours</div>
                    </div>
                `
              )
              .join("")}
        `;
    altRoutesDiv.innerHTML = html;
  }

  // Assign functions to window object to make them globally accessible
  window.switchToRoute = function (index) {
    clearMap();
    const route = mapState.alternativeRoutes[index];
    displayRoute(route, [], mapState.currentCheckpoints);
    mapState.map.fitBounds(
      L.polyline(decodePolyline(route.geometry)).getBounds()
    );
  };

  // Clear map
  function clearMap() {
    if (mapState.mainRoute) mapState.map.removeLayer(mapState.mainRoute);
    mapState.alternativeRoutes.forEach((route) =>
      mapState.map.removeLayer(route)
    );
    mapState.markers.forEach((marker) => mapState.map.removeLayer(marker));
    mapState.alternativeRoutes = [];
    mapState.markers = [];
  }

  // Decode polyline
  function decodePolyline(encoded) {
    let points = [];
    let index = 0,
      lat = 0,
      lng = 0;
    const len = encoded.length;

    while (index < len) {
      let b,
        shift = 0,
        result = 0;
      do {
        b = encoded.charAt(index++).charCodeAt(0) - 63;
        result |= (b & 0x1f) << shift;
        shift += 5;
      } while (b >= 0x20);
      lat += result & 1 ? ~(result >> 1) : result >> 1;

      shift = 0;
      result = 0;
      do {
        b = encoded.charAt(index++).charCodeAt(0) - 63;
        result |= (b & 0x1f) << shift;
        shift += 5;
      } while (b >= 0x20);
      lng += result & 1 ? ~(result >> 1) : result >> 1;

      points.push([lat * 1e-5, lng * 1e-5]);
    }
    return points;
  }

  // Enhanced display route info
  function displayRouteInfo(data) {
    const routeInfo = document.getElementById("routeInfo");
    const altRoutesDiv = document.getElementById("alternativeRoutes");
    if (!routeInfo || !altRoutesDiv) return;

    const mainRoute = data.main_route;
    const altRoutes = data.alternative_routes || [];
    const weather = data.route_info.weather_summary;

    // Format destinations for display
    const destinationsText = data.destinations
      .map((dest) => dest.name)
      .join(" → ");

    // Display main route info with enhanced UI
    routeInfo.innerHTML = `
        <div class="route-card active" onclick="switchToRoute('main')">
            <h6 class="mb-2"><i class="bi bi-star-fill text-warning me-2"></i>Primary Route</h6>
            <div class="route-stats">
                <span class="route-stat"><i class="bi bi-clock"></i> ${(
                  mainRoute.duration / 3600
                ).toFixed(1)}h</span>
                <span class="route-stat"><i class="bi bi-signpost"></i> ${(
                  mainRoute.distance / 1000
                ).toFixed(1)}km</span>
                <span class="route-stat"><i class="bi bi-thermometer-half"></i> ${weather.avg_temperature.toFixed(
                  1
                )}°C</span>
            </div>
            <div class="route-details">
                <div><i class="bi bi-info-circle"></i> Via ${getMainRoadNames(
                  mainRoute
                )}</div>
                <div><i class="bi bi-geo"></i> ${
                  data.source.name
                } → ${destinationsText}</div>
                <div><i class="bi bi-flag"></i> ${
                  data.checkpoints.length
                } stops</div>
            </div>
        </div>
    `;

    // Display weather information
    const weatherSummary = document.getElementById("weather-summary");
    weatherSummary.innerHTML = `
        <div class="weather-summary-card">
            <h6><i class="bi bi-thermometer-half me-2"></i>Route Weather Summary</h6>
            <div class="weather-stats">
                <div class="weather-stat">
                    <i class="bi bi-thermometer"></i>
                    <span>Average: ${weather.avg_temperature.toFixed(
                      1
                    )}°C</span>
                </div>
                <div class="weather-stat">
                    <i class="bi bi-thermometer-low"></i>
                    <span>Min: ${weather.min_temperature.toFixed(1)}°C</span>
                </div>
                <div class="weather-stat">
                    <i class="bi bi-thermometer-high"></i>
                    <span>Max: ${weather.max_temperature.toFixed(1)}°C</span>
                </div>
                <div class="weather-stat">
                    <i class="bi bi-droplet"></i>
                    <span>Humidity: ${weather.avg_humidity.toFixed(0)}%</span>
                </div>
            </div>
        </div>
    `;

    // Display container recommendations
    const containerRecs = document.getElementById("container-recommendations");
    const recs = data.route_info.container_recommendations;
    containerRecs.innerHTML = `
        <div class="container-recs-card">
            <h6><i class="bi bi-box-seam me-2"></i>Container Recommendations</h6>
            <div class="rec-type">${recs.container_type}</div>
            <div class="rec-settings">${recs.settings}</div>
            <ul class="rec-precautions">
                ${recs.precautions.map((p) => `<li>${p}</li>`).join("")}
            </ul>
        </div>
    `;
  }

  // Helper function to get main road names
  function getMainRoadNames(route) {
    try {
      const majorRoads = route.legs[0].steps
        .filter((step) => step.name && step.distance > 1000)
        .map((step) => step.name)
        .filter((name, index, self) => self.indexOf(name) === index)
        .slice(0, 2);
      return majorRoads.length ? majorRoads.join(" → ") : "local roads";
    } catch (e) {
      return "local roads";
    }
  }

  // Helper function to get difference text
  function getDifferenceText(route, mainRoute) {
    const timeDiff = route.duration - mainRoute.duration;
    const distDiff = route.distance - mainRoute.distance;

    let text = "";
    if (timeDiff > 0) {
      text += `${Math.round(timeDiff / 60)} min longer`;
    } else {
      text += `${Math.round(-timeDiff / 60)} min shorter`;
    }

    if (distDiff > 0) {
      text += `, ${(distDiff / 1000).toFixed(1)}km further`;
    } else {
      text += `, ${(-distDiff / 1000).toFixed(1)}km shorter`;
    }

    return text;
  }

  window.switchToRoute = function (routeIndex) {
    clearMap();

    // Update active route card styling
    document.querySelectorAll(".route-card").forEach((card) => {
      card.classList.remove("active");
    });

    if (routeIndex === "main") {
      const mainRoute = mapState.currentRoute;
      displayRoute(mainRoute, [], mapState.currentCheckpoints);
      document.querySelector(".route-card").classList.add("active");
    } else {
      const route = mapState.alternativeRoutes[routeIndex];
      displayRoute(route, [], mapState.currentCheckpoints);
      document
        .querySelectorAll(".route-card")
        [routeIndex + 1].classList.add("active");
    }
  };

  // Enhanced checkpoint display
  function displayCheckpoints(checkpoints) {
    const checkpointsList = document.getElementById("checkpointsList");
    if (!checkpointsList) return;

    checkpointsList.innerHTML = checkpoints
      .map(
        (point, index) => `
            <div class="checkpoint-card">
                <div class="checkpoint-header">
                    <strong><i class="bi bi-geo-alt-fill me-2"></i>${
                      point.name
                    }</strong>
                    <span class="arrival-time">
                        <i class="bi bi-clock"></i> Arrival: ${new Date(
                          point.arrival_time
                        ).toLocaleString()}
                    </span>
                </div>
                
                <div class="weather-info">
                    <div class="current-weather">
                        <h6><i class="bi bi-cloud me-2"></i>Current Weather</h6>
                        <div class="weather-stat">
                            <i class="bi bi-thermometer"></i>
                            ${point.current_weather.temperature.toFixed(1)}°C
                        </div>
                        <div class="weather-stat">
                            <i class="bi bi-droplet"></i>
                            ${point.current_weather.humidity}% humidity
                        </div>
                        <div class="weather-stat">
                            <i class="bi bi-cloud-rain"></i>
                            ${
                              point.current_weather.precipitation_prob
                            }% precipitation
                        </div>
                    </div>
                    
                    <div class="forecast-weather">
                        <h6><i class="bi bi-calendar-event me-2"></i>Forecast at Arrival</h6>
                        <div class="weather-stat">
                            <i class="bi bi-thermometer"></i>
                            ${point.forecast_weather.temperature.toFixed(1)}°C
                        </div>
                        <div class="weather-stat">
                            <i class="bi bi-droplet"></i>
                            ${point.forecast_weather.humidity}% humidity
                        </div>
                        <div class="weather-stat">
                            <i class="bi bi-cloud-rain"></i>
                            ${
                              point.forecast_weather.precipitation_prob
                            }% precipitation
                        </div>
                    </div>
                </div>
                
                <div class="checkpoint-footer">
                    <div class="coordinates">
                        <i class="bi bi-geo"></i>
                        ${point.coords[0].toFixed(
                          4
                        )}, ${point.coords[1].toFixed(4)}
                    </div>
                    ${
                      point.distance_from_start
                        ? `<div class="distance-info">
                            <i class="bi bi-signpost"></i>
                            ${point.distance_from_start.toFixed(
                              1
                            )} km from start
                            (${point.hours_from_start.toFixed(1)} hours)
                        </div>`
                        : ""
                    }
                </div>
            </div>
        `
      )
      .join("");
  }

  // Initialize when DOM is loaded
  $(document).ready(function () {
    if (!mapState.map && document.getElementById("map")) {
      // Initialize map only if not already initialized
      initMap();
      setupLocationInputs();
      setupDestinationControls(); // Add this new function call
      initializeLocationSelects();
    }
  });
});
