import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import GraphPage from "./pages/GraphPage";

export default function App() {
  return (
    <div
      className="h-screen w-screen overflow-hidden bg-charcoal-300"
      style={{
        backgroundImage:
          "linear-gradient(rgba(182,255,59,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(182,255,59,0.025) 1px, transparent 1px)",
        backgroundSize: "40px 40px",
      }}
    >
      <div className="h-full p-3">
        <Routes>
          <Route path="/" element={<GraphPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  );
}
