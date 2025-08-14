import { useState, useEffect } from "react";
import { useStore } from "./store";
import MapView from "./components/MapView";
import Sidebar from "./components/Sidebar";

export default function App() {
  const { selectedId, setSelectedId } = useStore();
  const [fuse, setFuse] = useState(null);
  const [status, setStatus] = useState("Click the map");
  const [showNamed, setShowNamed] = useState(() => {
    if (typeof localStorage !== "undefined") {
      const v = localStorage.getItem("showNamed");
      if (v !== null) return v === "true";
    }
    return true;
  });
  const [showUnnamed, setShowUnnamed] = useState(() => {
    if (typeof localStorage !== "undefined") {
      const v = localStorage.getItem("showUnnamed");
      if (v !== null) return v === "true";
    }
    return true;
  });

  useEffect(() => {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem("showNamed", showNamed);
    }
  }, [showNamed]);

  useEffect(() => {
    if (typeof localStorage !== "undefined") {
      localStorage.setItem("showUnnamed", showUnnamed);
    }
  }, [showUnnamed]);

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "320px 1fr",
        height: "100vh",
      }}
    >
      <Sidebar
        fuse={fuse}
        status={status}
        showNamed={showNamed}
        showUnnamed={showUnnamed}
        setShowNamed={setShowNamed}
        setShowUnnamed={setShowUnnamed}
      />
      <MapView
        showNamed={showNamed}
        showUnnamed={showUnnamed}
        selectedId={selectedId}
        setSelectedId={setSelectedId}
        setStatus={setStatus}
        setFuse={setFuse}
      />
    </div>
  );
}
