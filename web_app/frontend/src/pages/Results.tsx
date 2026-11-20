import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import quizApi from "../api/quizApi";
import { useQuizState } from "../context/QuizStateContext";

/**
 * Screen 4 — Results (R21-R25).
 * Reachable only after all questions are answered (locked otherwise).
 * Shows total questions, correct, incorrect and the percentage score
 * computed by the backend from the recorded Responses (R23) — never typed
 * in. In Testing Mode the correct answers are revealed here (R24).
 * Restart clears the session and returns to Quiz Configuration (R25).
 */
const Results: React.FC = () => {
  const navigate = useNavigate();
  const { state, resetSession } = useQuizState();
  const attemptId = state.attemptId;

  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [locked, setLocked] = useState(false);

  useEffect(() => {
    if (!attemptId) {
      setError("No completed quiz found. Start a quiz first.");
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    quizApi
      .getResults(attemptId)
      .then((data) => {
        if (!cancelled) {
          setResults(data);
          setError(null);
          setLocked(false);
        }
      })
      .catch((err: any) => {
        if (cancelled) return;
        if (err?.status === 403) {
          setLocked(true);
          setError(err?.detail || "Results are locked until every question is answered.");
        } else {
          setError(err?.detail || "The results could not be loaded");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attemptId]);

  const handleRestart = useCallback(() => {
    resetSession(); // clears attempt, answers and progress (R25)
    navigate("/configure");
  }, [navigate, resetSession]);

  if (loading) {
    return (
      <div className="ds-section">
        <h1 className="ds-heading">Results</h1>
        <p style={{ color: "var(--ds-muted)" }}>Loading results…</p>
      </div>
    );
  }

  if (locked || (!results && error)) {
    return (
      <div className="ds-section">
        <h1 className="ds-heading">Results</h1>
        <div className="ds-notice" role="alert">
          {locked ? "🔒 " : ""}
          {error}
        </div>
        {locked && (
          <button type="button" className="ds-btn ds-btn-primary" style={{ marginTop: "1rem" }} onClick={() => navigate("/quiz")}>
            Continue the quiz
          </button>
        )}
        {!locked && (
          <button type="button" className="ds-btn ds-btn-primary" style={{ marginTop: "1rem" }} onClick={() => navigate("/configure")}>
            Go to Quiz Configuration
          </button>
        )}
      </div>
    );
  }

  const isTesting = results?.mode === "testing";

  return (
    <div className="ds-section">
      <h1 className="ds-heading">Results</h1>
      <p style={{ color: "var(--ds-muted)", marginTop: 0 }}>
        <span className="ds-badge">{isTesting ? "Testing Mode" : "Learning Mode"}</span>
      </p>

      <div className="ds-grid-2" style={{ maxWidth: "720px" }}>
        <div className="ds-kpi">
          <span className="ds-kpi-value">{results.totalQuestions}</span>
          <span className="ds-kpi-label">Total questions</span>
        </div>
        <div className="ds-kpi">
          <span className="ds-kpi-value">{results.percentageScore}%</span>
          <span className="ds-kpi-label">Percentage score</span>
        </div>
        <div className="ds-kpi">
          <span className="ds-kpi-value">{results.correctCount}</span>
          <span className="ds-kpi-label">Correct answers</span>
        </div>
        <div className="ds-kpi">
          <span className="ds-kpi-value">{results.incorrectCount}</span>
          <span className="ds-kpi-label">Incorrect answers</span>
        </div>
      </div>

      <section style={{ marginTop: "1.5rem", maxWidth: "720px" }}>
        <h2 className="ds-heading" style={{ fontSize: "1.2rem" }}>
          {isTesting ? "Answer review (correct answers revealed)" : "Answer review"}
        </h2>
        {results.details.map((detail: any, index: number) => (
          <div key={detail.questionId} className="ds-card" style={{ padding: "1rem", marginBottom: "0.75rem" }}>
            <p style={{ fontWeight: 700, marginTop: 0 }}>
              {index + 1}. {detail.questionText}{" "}
              <span className="ds-badge" style={{ background: detail.isCorrect ? "rgba(16,185,129,0.15)" : "rgba(244,63,94,0.15)" }}>
                {detail.isCorrect ? "Correct" : "Incorrect"}
              </span>
            </p>
            <p style={{ margin: "0.25rem 0" }}>
              Your answer: {detail.selectedOptionText ?? "—"}
            </p>
            {(isTesting || !detail.isCorrect) && (
              <p style={{ margin: "0.25rem 0" }}>
                Correct answer: <strong>{detail.correctOptionText ?? "—"}</strong>
              </p>
            )}
            {detail.explanation && (
              <p style={{ margin: "0.25rem 0", color: "var(--ds-muted)" }}>Explanation: {detail.explanation}</p>
            )}
          </div>
        ))}
      </section>

      <div style={{ display: "flex", gap: "0.75rem", marginTop: "1rem", flexWrap: "wrap" }}>
        <button type="button" className="ds-btn ds-btn-primary" onClick={handleRestart}>
          Restart the quiz
        </button>
        <button type="button" className="ds-btn" onClick={() => navigate("/")}>
          Upload a new document
        </button>
      </div>
    </div>
  );
};

export default Results;
