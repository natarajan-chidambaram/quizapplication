import React from "react";
import { useLocation } from "react-router-dom";
import { useQuizState } from "../context/QuizStateContext";

/**
 * Non-clickable four-tab progress bar (R32-R34) shown on every screen:
 * 'Document upload', 'Quiz configuration', 'Quiz session', 'Results'.
 * Completed and current steps are highlighted; later steps stay visible but
 * greyed out. The tabs are plain labels — navigation happens only through
 * the in-screen buttons, never by clicking a tab. An Exit button on the top
 * left returns to the Document Upload page at any point (R35).
 */
const steps = [
  { label: "Document upload" },
  { label: "Quiz configuration" },
  { label: "Quiz session" },
  { label: "Results" },
];

const order: Record<string, number> = { "/": 0, "/configure": 1, "/quiz": 2, "/results": 3 };

const QuizNav: React.FC = () => {
  const location = useLocation();
  const { resetSession } = useQuizState();
  const currentStep = order[location.pathname] ?? 0;

  const handleExit = () => {
    resetSession(); // an exit abandons the running quiz (R35)
    window.location.assign("/");
  };

  return (
    <header className="ds-nav">
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", minWidth: 0 }}>
        <button
          type="button"
          className="ds-btn quiz-nav-exit"
          onClick={handleExit}
          aria-label="Exit to the Document Upload page"
        >
          Exit
        </button>
        <span style={{ fontSize: "1.4rem" }} role="img" aria-label="quiz">
          📝
        </span>
        <span className="ds-heading" style={{ fontSize: "1.15rem", marginBottom: 0 }}>
          FOQUS - Free and Open QUiz System
        </span>
      </div>
      <nav
        aria-label="Quiz progress"
        style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}
      >
        {steps.map((step, stepIndex) => {
          const done = stepIndex < currentStep;
          const active = stepIndex === currentStep;
          const upcoming = stepIndex > currentStep;
          return (
            <span
              key={step.label}
              aria-current={active ? "step" : undefined}
              className={`quiz-tab ${done ? "quiz-tab--done" : ""} ${active ? "quiz-tab--active" : ""} ${
                upcoming ? "quiz-tab--upcoming" : ""
              }`}
              title={
                done
                  ? `${step.label} (completed)`
                  : active
                    ? `${step.label} (current step)`
                    : `${step.label} (not reached yet)`
              }
            >
              {done ? "✓ " : ""}
              {step.label}
            </span>
          );
        })}
      </nav>
    </header>
  );
};

export default QuizNav;
