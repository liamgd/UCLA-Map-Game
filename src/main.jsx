import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
console.log("main.jsx loaded"); // add this
createRoot(document.getElementById("root")).render(<App />);
