import { useState } from "react";
import { useStore } from "./store";
import MapView from "./components/MapView";
import Sidebar from "./components/Sidebar";
import usePersistentState from "./usePersistentState";

export default function App() {
  const { selectedId, setSelectedId } = useStore();
  const [fuse, setFuse] = useState(null);
  const [status, setStatus] = useState("Click the map");
  const [showNamed, setShowNamed] = usePersistentState("showNamed", true);
  const [showUnnamed, setShowUnnamed] = usePersistentState("showUnnamed", true);
  const [colorBy, setColorBy] = usePersistentState("colorBy", "category");
  const [queryMode, setQueryMode] = useState(false);
  const [queryResults, setQueryResults] = useState({
    lngLat: null,
    point: null,
    features: [],
  });
  const [trainingMode, setTrainingMode] = useState(false);
  const [showPoints, setShowPoints] = usePersistentState("showPoints", false);

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
        colorBy={colorBy}
        setColorBy={setColorBy}
        queryMode={queryMode}
        setQueryMode={setQueryMode}
        queryResults={queryResults}
        trainingMode={trainingMode}
        setTrainingMode={setTrainingMode}
        showPoints={showPoints}
        setShowPoints={setShowPoints}
      />
      <MapView
        showNamed={showNamed}
        showUnnamed={showUnnamed}
        colorBy={colorBy}
        selectedId={selectedId}
        setSelectedId={setSelectedId}
        setStatus={setStatus}
        setFuse={setFuse}
        queryMode={queryMode}
        setQueryResults={setQueryResults}
        trainingMode={trainingMode}
        showPoints={showPoints}
      />
    </div>
  );
}
