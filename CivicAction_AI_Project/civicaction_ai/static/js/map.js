document.addEventListener("DOMContentLoaded", async () => {
  const el = document.getElementById("map");
  if (!el || typeof L === "undefined") return;
  const map = L.map("map").setView([12.9141, 74.8560], 11);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  }).addTo(map);
  try {
    const response = await fetch("/api/complaints");
    const reports = await response.json();
    const points = [];
    reports.forEach(r => {
      const lat = Number(r.latitude), lon = Number(r.longitude);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
      points.push([lat, lon]);
      L.marker([lat, lon]).addTo(map).bindPopup(
        `<b>#${r.id} · ${r.category}</b><br>${r.location}<br>Priority: ${r.priority}<br>Status: ${r.status}`
      );
    });
    if (points.length) map.fitBounds(points, {padding: [25, 25], maxZoom: 14});
  } catch (e) { console.error("Could not load map reports", e); }
});
