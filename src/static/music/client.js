// Use the globally set token instead:
const token = window.TOKEN;
// Dynamically determine WebSocket protocol and host
const ws_scheme = window.location.protocol === "https:" ? "wss" : "ws";
const socketUrl =
  ws_scheme + "://" + window.location.host + "/ws/sync/?token=" + token;
console.log("WebSocket URL:", socketUrl);
const socket = new WebSocket(socketUrl);

// Helper to format ms into m:ss
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
};

socket.onerror = function (error) {
  console.error("WebSocket error:", error);
};

socket.onclose = function () {
  console.log("WebSocket connection closed");
};