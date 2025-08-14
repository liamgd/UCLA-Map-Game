import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import Fuse from "fuse.js";
import { useStore } from "./store";
import SearchBox from "./components/SearchBox";

const BOUNDS = [
  [-118.46, 34.052],
  [-118.433, 34.082],
];

const LABEL_TILES = [
  "https://a.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png",
  "https://b.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png",
  "https://c.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png",
  "https://d.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png",
];

function featureBounds(f) {
  const b = new maplibregl.LngLatBounds();
  const polys =
    f.geometry.type === "Polygon"
      ? [f.geometry.coordinates]
      : f.geometry.coordinates;
  polys.forEach((rings) =>
    rings[0].forEach(([lng, lat]) => b.extend([lng, lat]))
  );
  return b;
}

export default function App() {
  const mapRef = useRef(null);
  const dataRef = useRef(null);
  const readyRef = useRef(false); // style + layers ready
  const selectedRef = useRef(""); // latest selected id
  const hoverRef = useRef("");
  const filterRef = useRef(null);
  const [status, setStatus] = useState("Click the map");
  const [fuse, setFuse] = useState(null);
  const [showNamed, setShowNamed] = useState(true);
  const [showUnnamed, setShowUnnamed] = useState(true);
  const { selectedId, setSelectedId } = useStore();

  const namedFilter = ["!=", ["coalesce", ["get", "name"], ""], ""];
  const unnamedFilter = ["==", ["coalesce", ["get", "name"], ""], ""];

  const computeBaseFilter = () => {
    if (showNamed && showUnnamed) return null;
    if (showNamed) return namedFilter;
    if (showUnnamed) return unnamedFilter;
    return ["==", ["get", "id"], ""]; // match nothing
  };

  const applyHover = () => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const layerId = "bldg-hover";
    if (!map.getLayer(layerId)) return;
    const base = filterRef.current;
    const idFilter = ["==", ["get", "id"], hoverRef.current];
    map.setFilter(layerId, base ? ["all", base, idFilter] : idFilter);
  };

  // helper: safely (re)apply highlight filter
  const applyHighlight = (id) => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const layerId = "bldg-hi";
    if (!map.getLayer(layerId)) return;
    const base = filterRef.current;
    const idFilter = ["==", ["get", "id"], id || ""];
    map.setFilter(layerId, base ? ["all", base, idFilter] : idFilter);
  };

  const applyBaseFilters = () => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const base = computeBaseFilter();
    filterRef.current = base;
    map.setFilter("bldg-fill", base);
    map.setFilter("bldg-outline", base);
    applyHover();
    applyHighlight(selectedRef.current);
  };

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
            paint: { "background-color": "#f0f2f5" },
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
    const hoverPopup = new maplibregl.Popup({
      closeButton: false,
      closeOnClick: false,
    });

    const categoryColor = [
      "match",
      ["get", "category"],
      "Academic",
      "#1f77b4",
      "Administrative",
      "#ff7f0e",
      "Athletic/Recreational",
      "#2ca02c",
      "Dining",
      "#d62728",
      "Libraries/Museums",
      "#9467bd",
      "Medical/Health",
      "#8c564b",
      "Other/Unknown",
      "#e377c2",
      "Performance/Venues",
      "#7f7f7f",
      "Residential",
      "#bcbd22",
      "Service/Support",
      "#17becf",
      "#6aa9ff",
    ];
    const fillColor = [
      "case",
      ["==", ["coalesce", ["get", "name"], ""], ""],
      "#cccccc",
      categoryColor,
    ];
    const buildingFillPaint = {
      "fill-color": fillColor,
      "fill-opacity": 0.25,
    };

    map.on("load", async () => {
      // basemap (raster, no labels)
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

      // campus data
      const res = await fetch("/campus.geojson");
      const data = await res.json();
      console.log("campus features", data.features?.length);
      console.log(data.features[0]);
      // Expect geometry.coordinates like [[[-118.45,34.07], …]]

      dataRef.current = data;
      map.addSource("campus", { type: "geojson", data });

      // building layers
      map.addLayer({
        id: "bldg-fill",
        type: "fill",
        source: "campus",
        paint: buildingFillPaint,
      });
      map.addLayer({
        id: "bldg-outline",
        type: "line",
        source: "campus",
        paint: { "line-color": "#1b6ef3", "line-width": 1 },
      });
      map.addLayer(
        {
          id: "bldg-hover",
          type: "fill",
          source: "campus",
          filter: ["==", ["get", "id"], ""],
          paint: { "fill-color": "#ffeb3b", "fill-opacity": 0.5 },
        },
        "bldg-outline"
      );
      // street labels overlay
      map.addSource("labels", {
        type: "raster",
        tiles: LABEL_TILES,
        tileSize: 256,
        attribution: "© OpenStreetMap contributors, © CARTO",
      });
      map.addLayer({ id: "labels", type: "raster", source: "labels" });
      map.addLayer({
        id: "bldg-hi",
        type: "line",
        source: "campus",
        filter: ["==", ["get", "id"], ""],
        paint: { "line-color": "#ff9f1c", "line-width": 3 },
      });

      // mark ready and (re)apply any pending highlight
      readyRef.current = true;
      applyBaseFilters();

      // rebuild highlight layer after any style reload (HMR/theme changes)
      map.on("styledata", () => {
        if (!map.getSource("campus")) return;
        if (!map.getLayer("bldg-fill")) {
          map.addLayer({
            id: "bldg-fill",
            type: "fill",
            source: "campus",
            paint: buildingFillPaint,
          });
        }
        if (!map.getLayer("bldg-outline")) {
          map.addLayer({
            id: "bldg-outline",
            type: "line",
            source: "campus",
            paint: { "line-color": "#1b6ef3", "line-width": 1 },
          });
        }
        if (!map.getLayer("bldg-hover")) {
          const before = map.getLayer("bldg-outline")
            ? "bldg-outline"
            : undefined;
          map.addLayer(
            {
              id: "bldg-hover",
              type: "fill",
              source: "campus",
              filter: ["==", ["get", "id"], ""],
              paint: { "fill-color": "#ffeb3b", "fill-opacity": 0.5 },
            },
            before
          );
        }
        if (!map.getSource("labels")) {
          map.addSource("labels", {
            type: "raster",
            tiles: LABEL_TILES,
            tileSize: 256,
            attribution: "© OpenStreetMap contributors, © CARTO",
          });
        }
        if (!map.getLayer("labels")) {
          const before = map.getLayer("bldg-hi") ? "bldg-hi" : undefined;
          map.addLayer(
            { id: "labels", type: "raster", source: "labels" },
            before
          );
        }
        if (!map.getLayer("bldg-hi")) {
          map.addLayer({
            id: "bldg-hi",
            type: "line",
            source: "campus",
            filter: ["==", ["get", "id"], selectedRef.current || ""],
            paint: { "line-color": "#ff9f1c", "line-width": 3 },
          });
        }
        applyBaseFilters();
      });

      // Fuse index for search
      setFuse(
        new Fuse(data.features, {
          keys: ["properties.name", "properties.aliases"],
          threshold: 0.3,
          ignoreLocation: true,
          minMatchCharLength: 2,
        })
      );

      // click selects feature
      map.on("click", "bldg-fill", (e) => {
        const f = e.features[0];
        setSelectedId(f.properties.id);
      });

      map.on("mousemove", "bldg-fill", (e) => {
        const f = e.features[0];
        hoverRef.current = f.properties.id;
        hoverPopup.setLngLat(e.lngLat).setText(f.properties.name).addTo(map);
        applyHover();
      });

      map.on("mouseleave", "bldg-fill", () => {
        hoverPopup.remove();
        hoverRef.current = "";
        applyHover();
      });

      map.getCanvas().style.cursor = "crosshair";
    });

    return () => {
      hoverPopup.remove();
      map.remove();
    };
  }, [setSelectedId]);

  useEffect(() => {
    applyBaseFilters();
  }, [showNamed, showUnnamed]);

  // react to selection changes safely
  useEffect(() => {
    selectedRef.current = selectedId || "";

    const map = mapRef.current;
    if (!map) return;

    // apply filter when ready; if not, defer until idle
    if (readyRef.current && map.isStyleLoaded()) {
      applyHighlight(selectedRef.current);
    } else {
      map.once("idle", () => applyHighlight(selectedRef.current));
    }

    if (!selectedId || !dataRef.current) {
      setStatus("Click the map");
      return;
    }

    const f = dataRef.current.features.find(
      (x) => x.properties.id === selectedId
    );
    if (f) {
      const center = featureBounds(f).getCenter();
      map.easeTo({ center, zoom: 17, duration: 800 });
      setStatus(`Selected: ${f.properties.name}`);
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
      <aside
        style={{
          padding: 12,
          borderRight: "1px solid #e7e7e7",
          position: "relative",
        }}
      >
        <h3 style={{ margin: "6px 0" }}>UCLA Map Trainer</h3>
        <SearchBox fuse={fuse} />
        <div style={{ marginTop: 8 }}>
          <label style={{ display: "block" }}>
            <input
              type="checkbox"
              checked={showNamed}
              onChange={(e) => setShowNamed(e.target.checked)}
            />
            <span style={{ marginLeft: 4 }}>Show named buildings</span>
          </label>
          <label style={{ display: "block", marginTop: 4 }}>
            <input
              type="checkbox"
              checked={showUnnamed}
              onChange={(e) => setShowUnnamed(e.target.checked)}
            />
            <span style={{ marginLeft: 4 }}>Show unnamed buildings</span>
          </label>
        </div>
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
