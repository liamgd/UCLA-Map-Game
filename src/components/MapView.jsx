import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import Fuse from "fuse.js";

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
  selectedId,
  setSelectedId,
  setStatus,
  setFuse,
}) {
  const mapRef = useRef(null);
  const dataRef = useRef(null);
  const readyRef = useRef(false); // style + layers ready
  const selectedRef = useRef(""); // latest selected id
  const hoverRef = useRef("");
  const filterRef = useRef(null);

  const hasName = ["!=", ["get", "name"], "Unnamed Building"];
  const noName = ["==", ["get", "name"], "Unnamed Building"];

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
      map.addLayer({
        id: "bldg-label",
        type: "symbol",
        source: "campus",
        filter: hasName,
        layout: buildingLabelLayout,
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

        // Ensure layers exist (add on TOP by omitting "before")
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
        if (!map.getLayer("bldg-label")) {
          map.addLayer({
            id: "bldg-label",
            type: "symbol",
            source: "campus",
            layout: buildingLabelLayout,
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
        const withBase = (b, extra) => [
          "all",
          ...(b ? [b] : []),
          ...(extra ? [extra] : []),
        ];
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
  }, [setFuse, setSelectedId]);

  useEffect(() => {
    applyBaseFilters();
  }, [showNamed, showUnnamed]);

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

  return <div id="map" style={{ width: "100%", height: "100%" }} />;
}
