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
      {/* Request update #2: every page stays visible across the top as a
          progress indicator. The current page is highlighted, pages that
          are finished show a completed badge, future pages are faded. */}
      <nav className="quiznav" aria-label="Quiz progress">
        {steps.map((step, stepIndex) => {
          const locked = stepIndex === 3 && !state.completed;
          const active = stepIndex === currentStep;
          // A page is finished once the user has moved past it.
          const done = stepIndex < currentStep;
          const classes = [
            "quiznav-step",
            active ? "quiznav-step--current" : "",
            done ? "quiznav-step--done" : "",
            !active && !done ? "quiznav-step--future" : "",
          ]
            .filter(Boolean)
            .join(" ");
          const badge = done ? "✓" : stepIndex + 1;
          return (
            <Link
              key={step.to}
              to={step.to}
              className={classes}
              aria-current={active ? "page" : undefined}
              aria-label={`${step.label}${done ? " (completed)" : active ? " (current)" : " (not started)"}`}
              title={locked ? "Results unlock after all questions are answered" : step.label}
            >
              <span className="quiznav-step-badge" aria-hidden="true">
                {badge}
              </span>
              {step.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
};

export default QuizNav;
