import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

const BOUNDS = [
  [-118.456, 34.058],
  [-118.433, 34.082],
]; // UCLA bbox

export default function App() {
  const mapRef = useRef(null);
  const [status, setStatus] = useState("Click the map");

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

      map.on("click", (e) => {
        // simple feedback: show the clicked building name if any
        const features = map.queryRenderedFeatures(e.point, {
          layers: ["bldg-fill"],
        });
        if (features.length) {
          const f = features[0];
          setStatus(`Inside: ${f.properties.name}`);
        } else {
          setStatus("Miss!");
        }
      });

      map.getCanvas().style.cursor = "crosshair";
    });

    return () => map.remove();
  }, []);

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
