import SearchBox from "./SearchBox";

export default function Sidebar({
  fuse,
  status,
  showNamed,
  showUnnamed,
  setShowNamed,
  setShowUnnamed,
  colorBy,
  setColorBy,
  queryMode,
  setQueryMode,
  queryResults,
  trainingMode,
  setTrainingMode,
  showPoints,
  setShowPoints,
}) {
  return (
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
        <label style={{ display: "block", marginTop: 4 }}>
          <input
            type="checkbox"
            checked={showPoints}
            onChange={(e) => setShowPoints(e.target.checked)}
          />
          <span style={{ marginLeft: 4 }}>Show polygon points</span>
        </label>
        <div style={{ marginTop: 8 }}>
          <div>Color by:</div>
          <label style={{ display: "block" }}>
            <input
              type="radio"
              name="colorBy"
              value="category"
              checked={colorBy === "category"}
              onChange={(e) => setColorBy(e.target.value)}
            />
            <span style={{ marginLeft: 4 }}>Category</span>
          </label>
          <label style={{ display: "block", marginTop: 4 }}>
            <input
              type="radio"
              name="colorBy"
              value="zone"
              checked={colorBy === "zone"}
              onChange={(e) => setColorBy(e.target.value)}
            />
            <span style={{ marginLeft: 4 }}>Zone</span>
          </label>
          <label style={{ display: "block", marginTop: 4 }}>
            <input
              type="radio"
              name="colorBy"
              value="none"
              checked={colorBy === "none"}
              onChange={(e) => setColorBy(e.target.value)}
            />
            <span style={{ marginLeft: 4 }}>None</span>
          </label>
        </div>
      </div>
      <button
        onClick={() => setQueryMode((m) => !m)}
        style={{
          marginTop: 8,
          padding: "6px 8px",
          background: queryMode ? "#ddeeff" : "#fff",
          border: "1px solid #ccd",
          borderRadius: 4,
          cursor: "pointer",
        }}
      >
        {queryMode ? "Exit query" : "Query at point"}
      </button>
      <button
        onClick={() => setTrainingMode((m) => !m)}
        style={{
          marginTop: 8,
          padding: "6px 8px",
          background: trainingMode ? "#ddeeff" : "#fff",
          border: "1px solid #ccd",
          borderRadius: 4,
          cursor: "pointer",
          display: "block",
        }}
      >
        {trainingMode ? "Exit training" : "Start training"}
      </button>
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
      {queryResults.lngLat && (
        <div
          style={{
            marginTop: 8,
            maxHeight: "30vh",
            overflowY: "auto",
            border: "1px solid #e0e0e0",
            borderRadius: 4,
            padding: 8,
            background: "#fff",
          }}
        >
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontWeight: "bold" }}>Clicked point</div>
            <pre
              style={{
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                fontSize: 12,
              }}
            >
              {JSON.stringify(
                { lngLat: queryResults.lngLat, point: queryResults.point },
                null,
                2
              )}
            </pre>
          </div>
          {queryResults.features.map((f, idx) => (
            <div key={idx} style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: "bold" }}>
                {f.properties.name || f.properties.id || `Feature ${idx + 1}`}
              </div>
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  fontSize: 12,
                }}
              >
                {JSON.stringify(f.properties, null, 2)}
              </pre>
            </div>
          ))}
        </div>
      )}
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
  );
}

