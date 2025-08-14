import SearchBox from "./SearchBox";

export default function Sidebar({
  fuse,
  status,
  showNamed,
  showUnnamed,
  setShowNamed,
  setShowUnnamed,
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
  );
}

