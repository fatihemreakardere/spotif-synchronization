// Retrieve the token and party code from the global variable and hidden element.
const token = window.TOKEN;
const partyCode = document.getElementById("party-code").textContent.trim();

// Determine WebSocket protocol (wss for HTTPS, ws for HTTP) and build the URL.
const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
const socketUrl = `${ws_scheme}://${window.location.host}/ws/sync/?token=${token}&party=${partyCode}`;
console.log("WebSocket URL:", socketUrl);

// Open the WebSocket connection.
const socket = new WebSocket(socketUrl);

let myConnectionId; // To store this client's unique connection id.
let isPlaying = false; // Global flag for current playback status.
let currentSyncTarget = null;  // The connection id that we are auto-following.
let syncThrottle = false;      // Throttle flag to avoid sending sync commands too frequently.

// Variables to store your local playback status.
let localTrackUri = "";
let localCurrentTime = 0;

const syncStatusElem = document.getElementById("sync-status");

// Helper function: Convert milliseconds to m:ss format.
const formatTime = (ms) => {
  const sec = Math.floor(ms / 1000);
  const minutes = Math.floor(sec / 60);
  const seconds = sec % 60;
  return minutes + ":" + (seconds < 10 ? "0" + seconds : seconds);
};

socket.onopen = function () {
  console.log("WebSocket connection established");
};

socket.onmessage = function (event) {
  const data = JSON.parse(event.data);
  console.log("Realtime Player Status:", data);

  // Handle the dedicated message that sends back this client's connection id.
  if (data.self_id) {
    myConnectionId = data.self_id;
    console.log("Received own connection ID:", myConnectionId);
    return;
  }

  // If the message is from self, update the main player UI and store local status.
  if (data.connection_id === myConnectionId) {
    document.getElementById("track-title").textContent =
      data.currently_playing || "No track playing";
    document.getElementById("artist").textContent =
      data.artist || "Unknown Artist";

    if (data.album_art) {
      const albumImage = document.getElementById("album-image");
      albumImage.src = data.album_art;
      albumImage.style.display = "block";
    }

    if (data.current_time && data.duration) {
      const percent = (data.current_time / data.duration) * 100;
      document.getElementById("progress").style.width = percent + "%";
      document.getElementById("current-time").textContent = formatTime(
        data.current_time
      );
      document.getElementById("total-time").textContent = formatTime(
        data.duration
      );
    }

    isPlaying = data.is_playing;
    const playBtn = document.getElementById("play-btn");
    if (playBtn) {
      playBtn.innerHTML = isPlaying ? "⏸" : "▶";
      playBtn.title = isPlaying ? "Pause" : "Play";
    }

    // Update local status variables for your own playback.
    localTrackUri = data.track_uri || "";
    localCurrentTime = data.current_time || 0;
  } else {
    // For messages from other participants, update or create their display element.
    if (data.connection_id) {
      let participantElem = document.getElementById(data.connection_id);
      if (!participantElem) {
        participantElem = document.createElement("div");
        participantElem.id = data.connection_id;
        participantElem.style.cursor = "pointer";
        // Add click listener to toggle following a participant.
        participantElem.addEventListener("click", function () {
          if (currentSyncTarget === this.id) {
            // Unfollow if already following.
            currentSyncTarget = null;
            this.style.border = "";
            syncStatusElem.textContent = "Not following anyone.";
            console.log("Stopped following", this.id);
          } else {
            // If following another participant, remove border from previous.
            if (currentSyncTarget) {
              const prevElem = document.getElementById(currentSyncTarget);
              if (prevElem) prevElem.style.border = "";
            }
            currentSyncTarget = this.id;
            this.style.border = "2px solid red";
            syncStatusElem.textContent = "Following participant " + this.id;
            console.log("Now following", this.id);
          }
        });
        document.getElementById("participants").appendChild(participantElem);
      }
      // Update the participant element's text and data attributes.
      participantElem.textContent = `${
        data.currently_playing || "No track"
      } (${data.current_time ? formatTime(data.current_time) : "0:00"}) - ${
        data.artist || "Unknown"
      }`;
      participantElem.setAttribute("data-track-uri", data.track_uri);
      participantElem.setAttribute("data-position-ms", data.current_time);

      // If this participant is the current sync target, check if we need to sync.
      if (data.connection_id === currentSyncTarget && !syncThrottle) {
        // Check if the target's track is different or if there is a > 5-second difference.
        if (
          (data.track_uri && data.track_uri !== localTrackUri) ||
          (data.current_time &&
            Math.abs(data.current_time - localCurrentTime) > 5000)
        ) {
          syncThrottle = true;
          console.log(
            "Auto-syncing to",
            data.connection_id,
            "- target track:",
            data.track_uri,
            "target time:",
            data.current_time,
            "local time:",
            localCurrentTime
          );
          socket.send(
            JSON.stringify({
              command: "sync",
              track_uri: data.track_uri,
              position_ms: data.current_time,
            })
          );
          // Throttle auto-sync commands to once per second.
          setTimeout(() => {
            syncThrottle = false;
          }, 1000);
        }
      }
    }
  }
};

socket.onerror = function (error) {
  console.error("WebSocket error:", error);
};

socket.onclose = function () {
  console.log("WebSocket connection closed");
};

// Add event listeners for the playback control buttons once the DOM is loaded.
document.addEventListener("DOMContentLoaded", function () {
  const previousBtn = document.getElementById("previous-btn");
  const playBtn = document.getElementById("play-btn");
  const nextBtn = document.getElementById("next-btn");

  if (previousBtn) {
    previousBtn.addEventListener("click", function () {
      socket.send(JSON.stringify({ command: "previous" }));
    });
  }
  if (playBtn) {
    playBtn.addEventListener("click", function () {
      // Toggle between play and pause commands.
      if (isPlaying) {
        socket.send(JSON.stringify({ command: "pause" }));
      } else {
        socket.send(JSON.stringify({ command: "play" }));
      }
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener("click", function () {
      socket.send(JSON.stringify({ command: "next" }));
    });
  }
});
