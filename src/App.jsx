import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import Fuse from "fuse.js";
import { useStore } from "./store";

const BOUNDS = [
  [-118.456, 34.058],
  [-118.433, 34.082],
]; // UCLA bbox

export default function App() {
  const mapRef = useRef(null);
  const [status, setStatus] = useState("Click the map");
  const fuseRef = useRef(null);
  const { selectedId, setSelectedId } = useStore();

  useEffect(() => {
    const map = new maplibregl.Map({
      container: "map",
      style: {
        version: 8,
        sources: {},
        layers: [
          {
            id: "bg",
            type: "background",
            paint: { "background-color": "#f6f7f9" },
          },
        ],
      },
      center: [-118.4452, 34.0689],
      zoom: 16,
      minZoom: 15,
      maxZoom: 19,
      maxBounds: BOUNDS,
      dragRotate: false,
      pitchWithRotate: false,
    });
    mapRef.current = map;

    map.on("load", async () => {
      // 1) No-label basemap (raster)
      map.addSource("basemap", {
        type: "raster",
        tiles: [
          "https://a.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png",
          "https://b.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png",
          "https://c.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png",
          "https://d.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png",
        ],
        tileSize: 256,
        attribution: "© OpenStreetMap contributors, © CARTO",
      });
      map.addLayer({ id: "basemap", type: "raster", source: "basemap" });

      // Optional: gentle dim so your polygons pop
      map.addLayer(
        {
          id: "dim",
          type: "background",
          paint: { "background-color": "#000", "background-opacity": 0.05 },
        },
        "bldg-fill"
      ); // insert just under your fills if you want

      // load your single file for both draw + hit
      map.addSource("campus", { type: "geojson", data: "/campus.geojson" });

      // fill + outline
      map.addLayer({
        id: "bldg-fill",
        type: "fill",
        source: "campus",
        paint: { "fill-color": "#6aa9ff", "fill-opacity": 0.25 },
      });
      map.addLayer({
        id: "bldg-outline",
        type: "line",
        source: "campus",
        paint: { "line-color": "#1b6ef3", "line-width": 1 },
      });

      map.addLayer({
        id: "bldg-hi",
        type: "line",
        source: "campus",
        filter: ["==", ["get", "id"], ""],
        paint: { "line-color": "#ff9f1c", "line-width": 3 },
      });

      const data = map.getSource("campus")._data;
      fuseRef.current = new Fuse(data.features, {
        keys: ["properties.name", "properties.aliases"],
        threshold: 0.3,
      });

      map.on("click", "bldg-fill", (e) => {
        const f = e.features[0];
        setSelectedId(f.properties.id);
      });

      map.getCanvas().style.cursor = "crosshair";
    });

    return () => map.remove();
  }, []);

  useEffect(() => {
    if (!mapRef.current || !selectedId) return;
    const map = mapRef.current;
    map.setFilter("bldg-hi", ["==", ["get", "id"], selectedId]);
    const f = map
      .getSource("campus")
      ._data.features.find((x) => x.properties.id === selectedId);
    if (f) {
      const b = new maplibregl.LngLatBounds();
      (f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates)
        .flat(2)
        .forEach(([lng, lat]) => b.extend([lng, lat]));
      map.fitBounds(b, { padding: 80, maxZoom: 18, duration: 600 });
      setStatus(`Inside: ${f.properties.name}`);
    }
  }, [selectedId]);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "320px 1fr",
        height: "100vh",
      }}
    >
      <aside style={{ padding: 12, borderRight: "1px solid #e7e7e7" }}>
        <h3 style={{ margin: "6px 0" }}>UCLA Map Trainer</h3>
        <input
          placeholder="Search buildings…"
          style={{ width: "100%", padding: 8, borderRadius: 8, border: "1px solid #ccd" }}
          onKeyDown={(e) => {
            if (e.key !== "Enter") return;
            const q = e.currentTarget.value.trim();
            if (!q) return;
            const hits = fuseRef.current.search(q);
            if (hits.length) setSelectedId(hits[0].item.properties.id);
          }}
        />
        <div
          style={{
            marginTop: 8,
            padding: 8,
            background: "#f3f5f8",
            borderRadius: 8,
          }}
        >
          {status}
        </div>
        <div
          style={{
            position: "absolute",
            bottom: 12,
            fontSize: 12,
            opacity: 0.7,
          }}
        >
          © OpenStreetMap contributors (ODbL)
        </div>
      </aside>
      <div id="map" style={{ width: "100%", height: "100%" }} />
    </div>
  );
}
