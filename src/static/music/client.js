// Use the globally set token instead:
const token = window.TOKEN;
// Append party code extracted from a DOM element (make sure it exists in your client HTML)
const partyCode = document.getElementById("party-code").textContent;
// Dynamically determine WebSocket protocol and host
const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
const socketUrl =
  ws_scheme + "://" + window.location.host + "/ws/sync/?token=" + token + "&party=" + partyCode;
console.log("WebSocket URL:", socketUrl);
const socket = new WebSocket(socketUrl);

let myConnectionId; // store own connection id

// Helper to format ms into m:ss
const formatTime = (ms) => {
  const sec = Math.floor(ms / 1000);
  const minutes = Math.floor(sec / 60);
  const seconds = sec % 60;
  return minutes + ":" + (seconds < 10 ? "0" + seconds : seconds);
};

let isPlaying = false; // global flag for current playback status

socket.onopen = function () {
  console.log("WebSocket connection established");
};

socket.onmessage = function (event) {
  const data = JSON.parse(event.data);
  console.log("Realtime Player Status:", data);

  // Save own connection id from dedicated message
  if (data.self_id) {
    myConnectionId = data.self_id;
    return;
  }

  // if the status belongs to current client, update main player
  if (data.connection_id === myConnectionId) {
    // Update track title; adjust fields if your API returns different key names
    document.getElementById("track-title").textContent =
      data.currently_playing || "No track playing";
    // Update artist if available
    document.getElementById("artist").textContent =
      data.artist || "Unknown Artist";

    // Update album art if provided (assume key 'album_art' is returned)
    if (data.album_art) {
      const albumImage = document.getElementById("album-image");
      albumImage.src = data.album_art;
      albumImage.style.display = "block";
    }

    // Update progress bar & times if current_time and duration are available
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

    // Update playback state and adjust play button icon accordingly
    isPlaying = data.is_playing;
    const playBtn = document.getElementById("play-btn");
    if (playBtn) {
      playBtn.innerHTML = isPlaying ? "⏸" : "▶";
      playBtn.title = isPlaying ? "Pause" : "Play";
    }
  } else {
    // For non-own statuses, update participants list
    if (data.connection_id) {
      let participantElem = document.getElementById(data.connection_id);
      if (!participantElem) {
        participantElem = document.createElement("div");
        participantElem.id = data.connection_id;
        document.getElementById("participants").appendChild(participantElem);
      }
      participantElem.textContent = `${data.currently_playing || "No track"} (${data.current_time ? formatTime(data.current_time) : "0:00"}) - ${data.artist || "Unknown"}`;
    }
  }
};

socket.onerror = function (error) {
  console.error("WebSocket error:", error);
};

socket.onclose = function () {
  console.log("WebSocket connection closed");
};

// Add event listeners for control buttons
document.addEventListener("DOMContentLoaded", function() {
  const previousBtn = document.getElementById("previous-btn");
  const playBtn = document.getElementById("play-btn");
  const nextBtn = document.getElementById("next-btn");

  if (previousBtn) {
    previousBtn.addEventListener("click", function() {
      socket.send(JSON.stringify({ command: "previous" }));
    });
  }
  if (playBtn) {
    playBtn.addEventListener("click", function() {
      // Toggle based on current state:
      if (isPlaying) {
        socket.send(JSON.stringify({ command: "pause" }));
      } else {
        socket.send(JSON.stringify({ command: "play" }));
      }
    });
  }
  if (nextBtn) {
    nextBtn.addEventListener("click", function() {
      socket.send(JSON.stringify({ command: "next" }));
    });
  }
});