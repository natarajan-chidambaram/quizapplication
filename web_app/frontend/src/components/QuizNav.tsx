import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useQuizState } from "../context/QuizStateContext";

/**
 * Nav bar on every screen (design-system classes). Results is visible but
 * guarded on the screen itself: it is only unlocked after all questions
 * are answered (R21).
 */
const steps = [
  { to: "/", label: "Document Upload" },
  { to: "/configure", label: "Quiz Configuration" },
  { to: "/quiz", label: "Quiz Session" },
  { to: "/results", label: "Results" },
];

const QuizNav: React.FC = () => {
  const location = useLocation();
  const { state } = useQuizState();
  const order: Record<string, number> = { "/": 0, "/configure": 1, "/quiz": 2, "/results": 3 };
  const currentStep = order[location.pathname] ?? 0;

  return (
    <header className="ds-nav">
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", minWidth: 0 }}>
        <span style={{ fontSize: "1.4rem" }} role="img" aria-label="quiz">
          📝
        </span>
        <Link to="/" className="ds-heading" style={{ fontSize: "1.15rem", marginBottom: 0, color: "#fff" }}>
          Document Quiz
        </Link>
      </div>
      <nav style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
        {steps.map((step, stepIndex) => {
          const locked = stepIndex === 3 && !state.completed;
          const active = stepIndex === currentStep;
          return (
            <Link
              key={step.to}
              to={step.to}
              aria-current={active ? "page" : undefined}
              title={locked ? "Results unlock after all questions are answered" : step.label}
              style={{
                color: "#fff",
                textDecoration: locked ? "none" : "none",
                opacity: locked ? 0.55 : active ? 1 : 0.8,
                fontWeight: active ? 700 : 500,
                padding: "0.25rem 0.6rem",
                borderRadius: "var(--ds-radius)",
                background: active ? "rgba(255,255,255,0.18)" : "transparent",
              }}
            >
              {locked ? "🔒 " : ""}
              {step.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
};

export default QuizNav;
