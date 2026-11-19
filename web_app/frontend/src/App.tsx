import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { QuizStateProvider } from "./context/QuizStateContext";
import QuizNav from "./components/QuizNav";
import Documentspage from "./pages/Documentspage";
import Quizconfig from "./pages/Quizconfig";
import Quizsession from "./pages/Quizsession";
import Results from "./pages/Results";

/**
 * Exactly four screens (R1, R2): Document Upload, Quiz Configuration,
 * Quiz Session, Results. No entity CRUD dashboards are routed or linked.
 */
function App() {
  return (
    <QuizStateProvider>
      <div className="ds-page">
        <QuizNav />
        <main className="ds-container" style={{ paddingBottom: "3rem" }}>
          <Routes>
            <Route path="/" element={<Documentspage />} />
            <Route path="/configure" element={<Quizconfig />} />
            <Route path="/quiz" element={<Quizsession />} />
            <Route path="/results" element={<Results />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </QuizStateProvider>
  );
}

export default App;
