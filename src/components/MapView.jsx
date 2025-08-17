import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import Fuse from "fuse.js";

const CATEGORY_COLOR_ENTRIES = [
  ["Academic/Research", "#1f77b4"],
  ["Lower Education", "#aec7e8"],
  ["Clinic/Health", "#8c564b"],
  ["Food Service", "#d62728"],
  ["Hospital", "#c49c94"],
  ["Library", "#9467bd"],
  ["Museum", "#c5b0d5"],
  ["Performing Arts", "#ff7f0e"],
  ["Playhouse", "#ffbb78"],
  ["Pool", "#17becf"],
  ["Stadium", "#ff9896"],
  ["Sports Court/Pitch", "#98df8a"],
  ["Sports Field", "#2ca02c"],
  ["Green Space", "#9edae5"],
  ["Parking Structure", "#7f7f7f"],
  ["Parking Lot", "#c7c7c7"],
  ["Operations", "#e377c2"],
  ["On-Campus Housing", "#bcbd22"],
  ["Off-Campus Housing", "#dbdb8d"],
  ["Unknown", "#f7b6d2"],
];

const CATEGORY_LEGEND = Array.from(
  new Map(CATEGORY_COLOR_ENTRIES.map(([k, v]) => [k, v])).entries()
);

const ZONE_LEGEND = [
  ["North Campus", "#1f77b4"],
  ["South Campus", "#2ca02c"],
  ["The Hill", "#d62728"],
  ["Westwood", "#ff7f0e"],
];

const colorExpr = (mode) => {
  if (mode === "category") {
    return [
      "match",
      ["get", "category"],
      ...CATEGORY_COLOR_ENTRIES.flat(),
      "#6aa9ff",
    ];
  }
  if (mode === "zone") {
    return [
      "match",
      ["get", "zone"],
      ...ZONE_LEGEND.flat(),
      "#6aa9ff",
    ];
  }
  return "#6aa9ff";
};

const fillColorFor = (mode) => [
  "case",
  ["==", ["coalesce", ["get", "name"], ""], ""],
  "#cccccc",
  colorExpr(mode),
];

const BOUNDS = [
  [-118.465, 34.052],
  [-118.433, 34.082],
];

const LABEL_TILES = [
  "https://a.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png",
  "https://b.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png",
  "https://c.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png",
  "https://d.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png",
];

const setFilterSafe = (map, layerId, f) => {
  map.setFilter(layerId, f ?? ["all"]);
};

const withBase = (base, extra) => [
  "all",
  ...(base ? [base] : []),
  ...(extra ? [extra] : []),
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

export default function MapView({
  showNamed,
  showUnnamed,
  colorBy,
  selectedId,
  setSelectedId,
  setStatus,
  setFuse,
  queryMode,
  setQueryResults,
  trainingMode,
}) {
  const mapRef = useRef(null);
  const dataRef = useRef(null);
  const readyRef = useRef(false); // style + layers ready
  const selectedRef = useRef(""); // latest selected id
  const hoverRef = useRef("");
  const hoverTimeoutRef = useRef(null);
  const filterRef = useRef(null);
  const colorByRef = useRef(colorBy);
  const queryModeRef = useRef(queryMode);
  const trainingModeRef = useRef(trainingMode);
  const targetRef = useRef(null);

  const startTrainingRound = () => {
    if (!dataRef.current) return;
    const candidates = dataRef.current.features.filter(
      (f) => f.properties.name
    );
    if (!candidates.length) return;
    const next = candidates[Math.floor(Math.random() * candidates.length)];
    targetRef.current = next;
    setStatus(`Find: ${next.properties.name}`);
  };

  useEffect(() => {
    queryModeRef.current = queryMode;
    if (!queryMode) {
      setQueryResults({ lngLat: null, point: null, features: [] });
    }
  }, [queryMode, setQueryResults]);

  useEffect(() => {
    trainingModeRef.current = trainingMode;
    if (trainingMode) {
      startTrainingRound();
    } else {
      targetRef.current = null;
      setStatus("Click the map");
    }
  }, [trainingMode, setStatus]);

  const UNNAMED_PREFIX = "Unnamed ";
  const hasName = [
    "!=",
    ["slice", ["get", "name"], 0, UNNAMED_PREFIX.length],
    UNNAMED_PREFIX,
  ];
  const noName = [
    "==",
    ["slice", ["get", "name"], 0, UNNAMED_PREFIX.length],
    UNNAMED_PREFIX,
  ];

  const computeBaseFilter = () => {
    if (showNamed && showUnnamed) return ["all"]; // no-op filter
    if (showNamed) return hasName;
    if (showUnnamed) return noName;
    return ["==", ["get", "id"], ""]; // match nothing
  };

  const applyHover = () => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const layerId = "bldg-hover";
    if (!map.getLayer(layerId)) return;
    const idFilterH = ["==", ["get", "id"], hoverRef.current];
    map.setFilter(layerId, withBase(filterRef.current, idFilterH));
  };

  const applyHighlight = (id) => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const layerId = "bldg-hi";
    if (!map.getLayer(layerId)) return;
    const idFilterHi = ["==", ["get", "id"], id || ""];
    map.setFilter(layerId, withBase(filterRef.current, idFilterHi));
  };

  const applyBaseFilters = () => {
    const map = mapRef.current;
    if (!map || !readyRef.current) return;
    const base = computeBaseFilter();
    filterRef.current = base;
    setFilterSafe(map, "bldg-fill", base);
    setFilterSafe(map, "bldg-outline", base);
    setFilterSafe(map, "bldg-label", withBase(base, hasName));
    applyHover();
    applyHighlight(selectedRef.current);
  };

  useEffect(() => {
    const map = new maplibregl.Map({
      container: "map",
      style: {
        version: 8,
        glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
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

    const buildingFillPaint = {
      "fill-color": fillColorFor(colorByRef.current),
      "fill-opacity": 0.25,
    };

    const buildingLabelLayout = {
      "text-field": ["get", "name"], // Use the 'name' property of each feature for the label text
      "text-anchor": "center", // Center the label text relative to the feature
      "text-size": [
        "interpolate", // Smoothly change values based on zoom level
        ["linear"], // Interpolation is linear (no easing curve)
        ["zoom"], // Base the interpolation on the current map zoom level
        14,
        0, // At zoom level 15 → text size is 0 (hidden)
        15,
        8, // At zoom level 16 → text size is 12px
        19,
        24, // At zoom level 19 → text size is 24px
      ],
    };

    const buildingLabelPaint = {
      "text-color": "#000000",
      "text-halo-color": "#ffffff",
      "text-halo-width": 1,
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

      data.features = data.features.filter((f) => f.properties.render === true);

      data.features.forEach((f) => {
        const p = f.properties;
        const name = p.name?.toLowerCase() || "";
        if (p.category === "Residential") {
          p.category = p.zone === "Westwood" ? "Off-Campus Housing" : "On-Campus Housing";
        } else if (p.category === "Athletic/Recreational") {
          if (name.includes("pool")) {
            p.category = "Pool";
          } else if (name.includes("stadium") || name.includes("pavilion")) {
            p.category = "Stadium";
          } else if (
            name.includes("court") ||
            name.includes("pitch") ||
            name.includes("tennis")
          ) {
            p.category = "Sports Court/Pitch";
          } else if (
            name.includes("field") ||
            name.includes("track") ||
            name.includes("intramural") ||
            name.includes("im field") ||
            name.includes("drake") ||
            name.includes("spaulding")
          ) {
            p.category = "Sports Field";
          } else {
            p.category = "Sports Field";
          }
        }
      });

      dataRef.current = data;
      if (trainingModeRef.current) startTrainingRound();
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
      map.addLayer({
        id: "bldg-label",
        type: "symbol",
        source: "campus",
        filter: hasName,
        layout: buildingLabelLayout,
        paint: buildingLabelPaint,
      });
      map.addLayer({
        id: "bldg-hover",
        type: "line",
        source: "campus",
        filter: ["==", ["get", "id"], ""],
        paint: { "line-color": "#ffeb3b", "line-width": 3 },
      });
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

      // Rebuild layers after style reload (HMR/theme changes) without recomputing filters
      map.on("styledata", () => {
        if (!map.getSource("campus")) return;

        const fill = fillColorFor(colorByRef.current);
        // Ensure layers exist (add on TOP by omitting "before")
        if (!map.getLayer("bldg-fill")) {
          map.addLayer({
            id: "bldg-fill",
            type: "fill",
            source: "campus",
            paint: { "fill-color": fill, "fill-opacity": 0.25 },
          });
        } else {
          map.setPaintProperty("bldg-fill", "fill-color", fill);
        }
        if (!map.getLayer("bldg-outline")) {
          map.addLayer({
            id: "bldg-outline",
            type: "line",
            source: "campus",
            paint: { "line-color": "#1b6ef3", "line-width": 1 },
          });
        }
        if (!map.getLayer("bldg-label")) {
          map.addLayer({
            id: "bldg-label",
            type: "symbol",
            source: "campus",
            layout: buildingLabelLayout,
            paint: buildingLabelPaint,
          });
        }
        if (!map.getLayer("bldg-hover")) {
          map.addLayer({
            id: "bldg-hover",
            type: "line",
            source: "campus",
            filter: ["==", ["get", "id"], ""],
            paint: { "line-color": "#ffeb3b", "line-width": 3 },
          });
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

        // Reapply the LAST-KNOWN base filter from the ref (no recompute)
        const base = filterRef.current || ["all"];
        map.setFilter("bldg-fill", base);
        map.setFilter("bldg-outline", base);
        map.setFilter("bldg-label", withBase(base, hasName));

        // Keep hover/highlight in sync with the same base
        // Reuse top-level withBase helper instead of redeclaring
        map.setFilter(
          "bldg-hover",
          withBase(base, ["==", ["get", "id"], hoverRef.current])
        );
        map.setFilter(
          "bldg-hi",
          withBase(base, ["==", ["get", "id"], selectedRef.current || ""])
        );
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

      // choose the smallest-area feature to prefer children over parents
      const smallestFeature = (features) =>
        features.reduce(
          (smallest, f) =>
            (f.properties.area ?? Infinity) <
            (smallest.properties.area ?? Infinity)
              ? f
              : smallest,
          features[0]
        );

      // click selects or queries features
      map.on("click", (e) => {
        const features = map.queryRenderedFeatures(e.point, {
          layers: ["bldg-fill"],
        });
        if (trainingModeRef.current) {
          if (features.length > 0) {
            const f = smallestFeature(features);
            setSelectedId(f.properties.id);
            if (
              targetRef.current &&
              f.properties.id === targetRef.current.properties.id
            ) {
              setStatus("Correct!");
              startTrainingRound();
            } else if (targetRef.current) {
              setStatus(`Try again: ${targetRef.current.properties.name}`);
            }
          }
          return;
        }
        if (queryModeRef.current) {
          setQueryResults({
            lngLat: { lng: e.lngLat.lng, lat: e.lngLat.lat },
            point: { x: e.point.x, y: e.point.y },
            features,
          });
          setStatus(
            `Found ${features.length} feature${features.length !== 1 ? "s" : ""}`
          );
        } else if (features.length > 0) {
          const f = smallestFeature(features);
          setSelectedId(f.properties.id);
        }
        if (features.length === 0) {
          setSelectedId(null);
        }
      });

      // hover quickly then refine to smallest feature after a short delay
      map.on("mousemove", "bldg-fill", (e) => {
        if (queryModeRef.current || trainingModeRef.current) return;
        if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
        const features = map.queryRenderedFeatures(e.point, {
          layers: ["bldg-fill"],
        });
        if (!features.length) return;
        const first = features[0];
        hoverRef.current = first.properties.id;
        hoverPopup.setLngLat(e.lngLat).setText(first.properties.name).addTo(map);
        applyHover();
        const point = e.point;
        const lngLat = e.lngLat;
        hoverTimeoutRef.current = setTimeout(() => {
          const features2 = map.queryRenderedFeatures(point, {
            layers: ["bldg-fill"],
          });
          if (!features2.length) return;
          const f = smallestFeature(features2);
          if (f.properties.id !== hoverRef.current) {
            hoverRef.current = f.properties.id;
            hoverPopup.setLngLat(lngLat).setText(f.properties.name).addTo(map);
            applyHover();
          }
        }, 100);
      });

      map.on("mouseleave", "bldg-fill", () => {
        if (queryModeRef.current || trainingModeRef.current) return;
        if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
        hoverPopup.remove();
        hoverRef.current = "";
        applyHover();
      });

      map.getCanvas().style.cursor = "crosshair";
    });

    return () => {
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
      hoverPopup.remove();
      map.remove();
    };
    }, [setFuse, setSelectedId, setStatus, setQueryResults]);

  useEffect(() => {
    applyBaseFilters();
  }, [showNamed, showUnnamed]);

  useEffect(() => {
    colorByRef.current = colorBy;
    const map = mapRef.current;
    if (!map) return;
    if (map.getLayer("bldg-fill")) {
      map.setPaintProperty("bldg-fill", "fill-color", fillColorFor(colorBy));
    }
  }, [colorBy]);

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
  }, [selectedId, setStatus]);

  const fitToCampus = () => {
    const map = mapRef.current;
    if (!map) return;
    map.fitBounds(BOUNDS, { padding: 20, duration: 800 });
  };

  return (
    <div style={{ width: "100%", height: "100%", position: "relative" }}>
      <div id="map" style={{ width: "100%", height: "100%" }} />
      <button
        onClick={fitToCampus}
        style={{
          position: "absolute",
          top: 12,
          right: 12,
          zIndex: 1,
          padding: "6px 8px",
          background: "#fff",
          border: "1px solid #ccd",
          borderRadius: 4,
          cursor: "pointer",
        }}
      >
        Fit to campus
      </button>
      {colorBy !== "none" && (
        <div
          style={{
            position: "absolute",
            bottom: 12,
            right: 12,
            background: "rgba(255,255,255,0.9)",
            padding: 8,
            borderRadius: 4,
            fontSize: 12,
            maxHeight: "50%",
            overflowY: "auto",
          }}
        >
          {(colorBy === "category" ? CATEGORY_LEGEND : ZONE_LEGEND).map(
            ([label, color]) => (
              <div
                key={label}
                style={{ display: "flex", alignItems: "center", marginBottom: 2 }}
              >
                <span
                  style={{
                    width: 12,
                    height: 12,
                    background: color,
                    border: "1px solid #ccc",
                    marginRight: 4,
                  }}
                />
                {label}
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
}
