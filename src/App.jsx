import { useState } from "react";
import { useStore } from "./store";
import MapView from "./components/MapView";
import Sidebar from "./components/Sidebar";

export default function App() {
  const { selectedId, setSelectedId } = useStore();
  const [fuse, setFuse] = useState(null);
  const [status, setStatus] = useState("Click the map");
  const [showNamed, setShowNamed] = useState(true);
  const [showUnnamed, setShowUnnamed] = useState(true);
  const [colorBy, setColorBy] = useState("category");
  const [queryMode, setQueryMode] = useState(false);
  const [queryResults, setQueryResults] = useState([]);
  const [trainingMode, setTrainingMode] = useState(false);

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
      />
    </div>
  );
}
