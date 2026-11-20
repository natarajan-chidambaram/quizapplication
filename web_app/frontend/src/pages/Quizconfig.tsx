import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import quizApi from "../api/quizApi";
import { useQuizState } from "../context/QuizStateContext";

/**
 * Screen 2 — Quiz Configuration (R8-R11).
 * Learning/Testing mode, number of questions (limited to what the document
 * provides), sequential/random order, then Start the quiz.
 */
const Quizconfig: React.FC = () => {
  const navigate = useNavigate();
  const { state, configure, startAttempt } = useQuizState();
  const [questions, setQuestions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<"learning" | "testing">(state.mode ?? "learning");
  const [questionOrder, setQuestionOrder] = useState<"sequential" | "random">(state.questionOrder ?? "sequential");
  const [timerScope, setTimerScope] = useState<"per_question" | "per_session">(state.timerScope ?? "per_question");
  const [timerDurationSeconds, setTimerDurationSeconds] = useState<number>(state.timerDurationSeconds || 60);
  const [questionCount, setQuestionCount] = useState<number | null>(null);
  const [difficulty, setDifficulty] = useState<string>("all");
  const [questionType, setQuestionType] = useState<"audio" | "mcq">("mcq");
  const difficulties = Array.from(
    new Set(questions.map((question: any) => question?.difficulty).filter(Boolean) as string[])
  ).sort();
  // How many questions survive the difficulty + question-type filters (R11-R14)
  const availableCount = questions.filter((question: any) => {
    const matchesDifficulty = difficulty === "all" || question?.difficulty === difficulty;
    const matchesType = questionType === "mcq" || Boolean(question?.audioSentence);
    return matchesDifficulty && matchesType;
  }).length;

  useEffect(() => {
    if (!state.documentId) {
      setError("No document selected. Upload a document first.");
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    quizApi
      .documentQuestions(state.documentId)
      .then((data) => {
        if (!cancelled) {
          const loaded = Array.isArray(data) ? data : [];
          setQuestions(loaded);
          setQuestionCount(null); // R15: an unset count means 'use all questions'
        }
      })
      .catch((err: any) => {
        if (!cancelled) setError(err?.detail || "Could not load the questions of this document");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [state.documentId]);

  const handleStart = useCallback(async () => {
    if (!state.documentId) return;
    setStarting(true);
    setError(null);
    try {
      const result = await quizApi.startQuiz({
        documentId: state.documentId,
        mode,
        questionOrder,
        questionCount,
        timerScope,
        timerDurationSeconds,
        difficulty: difficulty === "all" ? null : difficulty,
        questionType,
      });
      configure(mode, questionOrder, timerScope, timerDurationSeconds);
      startAttempt(
        result.attempt.id,
        result.questionIds.length,
        result.mode,
        result.questionOrder
      );
      navigate("/quiz");
    } catch (err: any) {
      setError(err?.detail || "The quiz could not be started");
    } finally {
      setStarting(false);
    }
  }, [configure, mode, navigate, questionCount, questionOrder, startAttempt, state.documentId, timerDurationSeconds, timerScope]);

  if (!state.documentId) {
    return (
      <div className="ds-section">
        <h1 className="ds-heading">Quiz Configuration</h1>
        <div className="ds-notice" role="alert">
          No document selected. Please upload and select a document first.
        </div>
        <button type="button" className="ds-btn ds-btn-primary" style={{ marginTop: "1rem" }} onClick={() => navigate("/")}>
          Go to Document Upload
        </button>
      </div>
    );
  }

  return (
    <div className="ds-section">
      <h1 className="ds-heading">Quiz Configuration</h1>
      <p style={{ color: "var(--ds-muted)", marginTop: 0 }}>
        Document: <strong>{state.documentName}</strong>
      </p>

      {loading ? (
        <p style={{ color: "var(--ds-muted)" }}>Loading the document's questions…</p>
      ) : questions.length === 0 ? (
        <>
          <div className="ds-notice" role="alert">
            This document contains no questions. Please upload a different document.
          </div>
          <button type="button" className="ds-btn" style={{ marginTop: "1rem" }} onClick={() => navigate("/")}>
            Back to Document Upload
          </button>
        </>
      ) : (
        <section className="ds-card" style={{ padding: "1.25rem", maxWidth: "640px" }}>
          <div className="ds-field">
            <span className="ds-label">Mode</span>
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              <label style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                <input
                  type="radio"
                  name="quiz-mode"
                  value="learning"
                  checked={mode === "learning"}
                  onChange={() => setMode("learning")}
                />
                Learning Mode
              </label>
              <label style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                <input
                  type="radio"
                  name="quiz-mode"
                  value="testing"
                  checked={mode === "testing"}
                  onChange={() => setMode("testing")}
                />
                Testing Mode
              </label>
            </div>
            <span style={{ color: "var(--ds-muted)", fontSize: "0.85rem" }}>
              {mode === "learning"
                ? "Correctness, the correct answer and any explanation are shown right after each answer."
                : "Correctness and answers stay hidden until the quiz is completed."}
            </span>
          </div>

          <div className="ds-field">
            <label className="ds-label" htmlFor="question-type">
              Question type
            </label>
            <select
              id="question-type"
              className="ds-input"
              value={questionType}
              onChange={(event) => setQuestionType(event.target.value as "audio" | "mcq")}
            >
              <option value="mcq">MCQ — all questions</option>
              <option value="audio">Audio (listening) — questions with an audio sentence</option>
            </select>
            <span style={{ color: "var(--ds-muted)", fontSize: "0.85rem" }}>
              {questionType === "audio"
                ? "Only the questions whose document carries an 'audio sentence' are played, read aloud by the browser."
                : "All questions of the document can be selected."}
            </span>
          </div>

          <div className="ds-field">
            <label className="ds-label" htmlFor="difficulty">
              Difficulty
            </label>
            <select
              id="difficulty"
              className="ds-input"
              value={difficulty}
              onChange={(event) => setDifficulty(event.target.value)}
            >
              <option value="all">All difficulties</option>
              {difficulties.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
            <span style={{ color: "var(--ds-muted)", fontSize: "0.85rem" }}>
              {difficulties.length === 0
                ? "This document has no difficulty tags, so every question stays available."
                : `Only the questions tagged with the chosen difficulty are used.`}
            </span>
          </div>

          <div className="ds-field">
            <label className="ds-label" htmlFor="question-count">
              Number of questions ({availableCount} match the filters, {questions.length} in the document)
            </label>
            <select
              id="question-count"
              className="ds-input"
              value={questionCount === null ? "all" : String(questionCount)}
              onChange={(event) =>
                setQuestionCount(event.target.value === "all" ? null : Number(event.target.value))
              }
            >
              <option value="all">All matching questions</option>
              {questions.map((_, index) => (
                <option key={index + 1} value={index + 1}>
                  {index + 1}
                </option>
              ))}
            </select>
          </div>

          <div className="ds-field">
            <span className="ds-label">Question order</span>
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              <label style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                <input
                  type="radio"
                  name="question-order"
                  value="sequential"
                  checked={questionOrder === "sequential"}
                  onChange={() => setQuestionOrder("sequential")}
                />
                Sequential
              </label>
              <label style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                <input
                  type="radio"
                  name="question-order"
                  value="random"
                  checked={questionOrder === "random"}
                  onChange={() => setQuestionOrder("random")}
                />
                Random
              </label>
            </div>
          </div>

          <div className="ds-field">
            <span className="ds-label">Timer</span>
            <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
              <label style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                <input
                  type="radio"
                  name="timer-scope"
                  value="per_question"
                  checked={timerScope === "per_question"}
                  onChange={() => setTimerScope("per_question")}
                />
                Per question
              </label>
              <label style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                <input
                  type="radio"
                  name="timer-scope"
                  value="per_session"
                  checked={timerScope === "per_session"}
                  onChange={() => setTimerScope("per_session")}
                />
                Entire session
              </label>
            </div>
            <div className="ds-field" style={{ marginTop: "0.75rem", maxWidth: "240px" }}>
              <label className="ds-label" htmlFor="timer-duration">
                Time allotted ({timerScope === "per_question" ? "per question" : "for the whole session"})
              </label>
              <select
                id="timer-duration"
                className="ds-input"
                value={timerDurationSeconds}
                onChange={(event) => setTimerDurationSeconds(Number(event.target.value))}
              >
                {[30, 60, 120, 180, 300, 600].map((seconds) => (
                  <option key={seconds} value={seconds}>
                    {seconds >= 60 ? `${seconds / 60} minute${seconds > 60 ? "s" : ""}` : `${seconds} seconds`}
                  </option>
                ))}
              </select>
            </div>
            <span style={{ color: "var(--ds-muted)", fontSize: "0.85rem" }}>
              {timerScope === "per_question"
                ? "The timer resets for every question and counts that question's remaining time."
                : "One timer counts down the remaining time for the entire quiz."}
            </span>
          </div>

          {error && (
            <div className="ds-notice" role="alert" style={{ borderColor: "var(--ds-primary)", marginBottom: "1rem" }}>
              {error}
            </div>
          )}

          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <button
              type="button"
              className="ds-btn"
              onClick={() => navigate("/")}
              aria-label="Back to the Document Upload page"
            >
              ← Back to Document Upload
            </button>
            <button type="button" className="ds-btn ds-btn-primary" onClick={handleStart} disabled={starting}>
              {starting ? "Starting the quiz…" : "Start the quiz"}
            </button>
          </div>
        </section>
      )}
    </div>
  );
};

export default Quizconfig;
