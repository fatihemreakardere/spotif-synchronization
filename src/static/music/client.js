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

  // Update this client's main player UI if the status message is from self.
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
  } else {
    // For status messages from other participants, update the participants list.
    if (data.connection_id) {
      let participantElem = document.getElementById(data.connection_id);
      if (!participantElem) {
        participantElem = document.createElement("div");
        participantElem.id = data.connection_id;
        participantElem.style.cursor = "pointer";
        // Add click listener to trigger the sync functionality.
        participantElem.addEventListener("click", function () {
          const trackUri = this.getAttribute("data-track-uri");
          const positionMs = parseInt(this.getAttribute("data-position-ms"), 10);
          if (trackUri && !isNaN(positionMs)) {
            console.log("Syncing to track:", trackUri, "at", positionMs, "ms");
            socket.send(
              JSON.stringify({
                command: "sync",
                track_uri: trackUri,
                position_ms: positionMs,
              })
            );
          } else {
            console.error("Missing sync parameters for participant", data.connection_id);
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
