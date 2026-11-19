"""Document-based quiz workflow services (R3-R7, R9-R11, R14-R15, R21-R24).

Parsing (JSON or PDF), validation (>=2 options, exactly one correct answer)
and the session/answer services shared by the upload, start, session, answer
and results endpoints. Nothing here invents questions: every question and
option comes from the uploaded document (R7).
"""

from __future__ import annotations

import io
import json
import os
import random
import re
from datetime import datetime
from typing import Any, List, Optional

UPLOAD_DIR = os.path.join("data", "uploads")

ALLOWED_EXTENSIONS = {".json", ".pdf"}
ALLOWED_CONTENT_TYPES = {"application/json", "application/pdf"}


class DocumentValidationError(ValueError):
    """The uploaded document is not a valid multiple-choice document (R5)."""


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _first(mapping: Any, *names: str) -> Any:
    for name in names:
        if isinstance(mapping, dict) and mapping.get(name) is not None:
            return mapping[name]
    return None


def detect_kind(filename: str, content_type: str) -> str:
    """'json' or 'pdf', from the extension first and the content type second."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in ALLOWED_EXTENSIONS:
        return "pdf" if ext == ".pdf" else "json"
    if (content_type or "").lower() in ALLOWED_CONTENT_TYPES:
        return "pdf" if "pdf" in content_type.lower() else "json"
    raise DocumentValidationError("Only JSON or PDF files can be uploaded")


def parse_document(kind: str, raw: bytes) -> dict:
    """Parse raw bytes into {'questions': [{text, explanation, options: [{text, isCorrect}]}]}."""
    questions = _parse_json(raw) if kind == "json" else _parse_pdf(raw)
    return _finalize(questions)


############################################
# JSON parsing
############################################


def _parse_json(raw: bytes) -> List[dict]:
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except Exception as exc:
        raise DocumentValidationError(f"The file is not valid JSON: {exc}")
    source = _extract_question_list(data)
    if not source:
        raise DocumentValidationError(
            "The JSON document contains no questions (expected a list or a 'questions' key)"
        )
    questions = []
    for index, item in enumerate(source):
        if not isinstance(item, dict):
            raise DocumentValidationError(f"Question {index + 1} is not a JSON object")
        text = _norm(_first(item, "text", "question", "prompt", "title", "statement"))
        if not text:
            raise DocumentValidationError(f"Question {index + 1} has no text")
        explanation = (
            _norm(_first(item, "explanation", "rationale", "explanationText")) or None
        )
        options_raw = (
            _first(item, "options", "choices", "answers", "answerOptions") or []
        )
        if not isinstance(options_raw, list):
            raise DocumentValidationError(
                f"Question {index + 1}: options must be a list"
            )
        options: List[dict] = []
        for option_item in options_raw:
            if isinstance(option_item, dict):
                option_text = _norm(
                    _first(option_item, "text", "option", "label", "choice", "value")
                )
                correct = (
                    _first(option_item, "isCorrect", "is_correct", "correct") is True
                )
            else:
                option_text = _norm(option_item)
                correct = False
            options.append({"text": option_text, "isCorrect": correct})
        questions.append(
            {
                "text": text,
                "explanation": explanation,
                "options": options,
                "correctToken": _first(
                    item, "correctAnswer", "answer", "answerKey", "correct_option"
                ),
            }
        )
    return questions


def _extract_question_list(data: Any) -> Optional[list]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("questions", "questionList", "items", "mcqs", "quiz"):
            value = data.get(key)
            if isinstance(value, list):
                return value
        if any(
            key in data for key in ("text", "question", "prompt", "options", "choices")
        ):
            return [data]
    return None


############################################
# PDF parsing
############################################

_OPTION_MARKER = re.compile(r"(?:^|\s)\(?([A-Ha-h])\s*[).:\]]\s*")
_QUESTION_START = re.compile(
    r"^(?:Q(?:uestion)?\s*)?(\d{1,3})\s*[.):]\s*(.+)$", re.IGNORECASE
)
_ANSWER_LINE = re.compile(
    r"^(?:correct\s*answers?|answers?|ans|key)\s*[:\-]\s*(.+)$", re.IGNORECASE
)
_EXPLANATION_LINE = re.compile(r"^explanation\s*[:\-]\s*(.*)$", re.IGNORECASE)
_STANDALONE_OPTION = re.compile(r"^\(?([A-Ha-h])\s*[).:\]]\s*(.*)$")


def _parse_pdf(raw: bytes) -> List[dict]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise DocumentValidationError("PDF support is not available on the server")
    try:
        reader = PdfReader(io.BytesIO(raw))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as exc:
        raise DocumentValidationError(f"The PDF could not be read: {exc}")
    if not _norm(text):
        raise DocumentValidationError(
            "No text could be extracted from the PDF; scanned image PDFs are not supported"
        )

    questions: List[dict] = []
    current: Optional[dict] = None
    in_options = False

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        answer_match = _ANSWER_LINE.match(line)
        explanation_match = _EXPLANATION_LINE.match(line)
        if current is not None and answer_match:
            current["correctToken"] = answer_match.group(1)
            in_options = False
            continue
        if current is not None and explanation_match and current["options"]:
            tail = explanation_match.group(1)
            current["explanation"] = (
                _norm(f"{current.get('explanation') or ''} {tail}") or None
            )
            continue
        if _QUESTION_START.match(line):
            match = _QUESTION_START.match(line)
            body = match.group(2)
            head, inline_options = _split_inline_options(body)
            current = {
                "text": _norm(head),
                "explanation": None,
                "options": [],
                "correctToken": None,
            }
            questions.append(current)
            for option_text in inline_options:
                _append_pdf_option(current, option_text)
            in_options = True
            continue
        standalone = _STANDALONE_OPTION.match(line)
        if current is not None and standalone and current["text"]:
            _append_pdf_option(current, line)
            in_options = True
            continue
        if current is None:
            continue  # preamble text before the first question is ignored
        if in_options and current["options"]:
            current["options"][-1]["raw"] = _norm(
                f"{current['options'][-1]['raw']} {line}"
            )
        else:
            current["text"] = _norm(f"{current['text']} {line}")

    parsed = []
    for item in questions:
        options = []
        for option in item["options"]:
            text = option["raw"]
            correct = False
            if text.startswith("*") or text.startswith("\u2713"):
                correct = True
                text = text.lstrip("*\u2713 ")
            options.append({"text": _norm(text), "isCorrect": correct})
        parsed.append(
            {
                "text": item["text"],
                "explanation": item["explanation"],
                "options": options,
                "correctToken": item["correctToken"],
            }
        )
    if not parsed:
        raise DocumentValidationError(
            "No multiple-choice questions were found in the PDF (expected numbered questions "
            "with lettered options such as '1. Question? A) ... B) ...' and an 'Answer: B' line)"
        )
    return parsed


def _split_inline_options(body: str):
    """Split 'What is 2+2? A) 3 B) 4' into question text and option texts."""
    matches = list(_OPTION_MARKER.finditer(body))
    if not matches:
        return body, []
    first = matches[0]
    head = body[: first.start()].strip()
    if not head:
        return body, []
    options = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        segment = body[start:end].strip()
        if segment:
            options.append(segment)
    return head, options


def _append_pdf_option(question: dict, raw_line: str) -> None:
    match = _STANDALONE_OPTION.match(raw_line)
    text = match.group(2) if match else raw_line
    question["options"].append({"raw": _norm(text)})


############################################
# Shared validation (R4, R5)
############################################


def _finalize(questions: List[dict]) -> dict:
    validated = []
    for index, item in enumerate(questions):
        number = index + 1
        options = item["options"]
        if len(options) < 2:
            raise DocumentValidationError(
                f"Question {number} ('{item['text'][:60]}') needs at least 2 answer options"
            )
        for option in options:
            if not option["text"]:
                raise DocumentValidationError(
                    f"Question {number} has an empty answer option"
                )
        marked = [i for i, option in enumerate(options) if option["isCorrect"]]
        token = item.get("correctToken")
        if not marked and token is not None:
            resolved = _resolve_correct_index(token, options, number)
            if resolved is None:
                raise DocumentValidationError(
                    f"Question {number}: the correct answer '{token}' does not match any option"
                )
            marked = [resolved]
        if len(marked) == 0:
            raise DocumentValidationError(
                f"Question {number} ('{item['text'][:60]}') has no marked correct answer"
            )
        if len(marked) > 1:
            raise DocumentValidationError(
                f"Question {number} has more than one correct answer"
            )
        options[marked[0]]["isCorrect"] = True
        validated.append(
            {
                "text": item["text"],
                "explanation": item.get("explanation") or None,
                "options": [
                    {"text": option["text"], "isCorrect": option["isCorrect"]}
                    for option in options
                ],
            }
        )
    return {"questions": validated}


def _resolve_correct_index(
    token: Any, options: List[dict], number: int
) -> Optional[int]:
    if isinstance(token, bool):
        return None
    if isinstance(token, int):
        if 0 <= token < len(options):
            return token
        if 1 <= token <= len(options):
            return token - 1
        return None
    if isinstance(token, float) and token.is_integer():
        return _resolve_correct_index(int(token), options, number)
    text = _norm(token)
    if not text:
        return None
    if len(text) == 1 and text.isalpha():
        letter = text.upper()
        index = ord(letter) - ord("A")
        if 0 <= index < len(options):
            return index
        return None
    if text.isdigit():
        return _resolve_correct_index(int(text), options, number)
    lowered = text.casefold()
    for index, option in enumerate(options):
        if _norm(option["text"]).casefold() == lowered:
            return index
    return None


############################################
# Persistence + session services
############################################


def store_document(
    db, filename: str, content_type: str, size: int, raw: bytes, parsed: dict
):
    """Persist the uploaded file, its Quiz and its Questions/Options (R6)."""
    from sql_alchemy import PDFDocument, Question, Option, Quiz
    from uuid import uuid4

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = (
        re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.basename(filename)) or "document"
    )
    storage_path = os.path.join(UPLOAD_DIR, f"{uuid4().hex}_{safe_name}")
    with open(storage_path, "wb") as handle:
        handle.write(raw)

    quiz = Quiz(
        title=os.path.splitext(os.path.basename(filename))[0] or "Uploaded quiz",
        description=f"Questions extracted from uploaded document {filename}",
        createdByUserId="",
        isPublished=False,
    )
    db.add(quiz)
    db.flush()

    questions = []
    for index, item in enumerate(parsed["questions"]):
        question = Question(
            quizId=quiz.id,
            text=item["text"],
            instructions="",
            questionType="multiple_choice",
            orderIndex=index + 1,
            explanation=item["explanation"],
            quiz_id=quiz.id,
        )
        db.add(question)
        db.flush()
        for order, option_item in enumerate(item["options"]):
            db.add(
                Option(
                    questionId=question.id,
                    optionText=option_item["text"],
                    optionOrder=order + 1,
                    isCorrect=bool(option_item["isCorrect"]),
                    question_id=question.id,
                )
            )
        db.flush()
        questions.append(question)

    document = PDFDocument(
        fileName=os.path.basename(filename),
        contentType=content_type,
        fileSizeBytes=size,
        uploadDate=datetime.now(),
        uploadedByUserId="",
        storagePath=storage_path,
        pDFDocumentQuiz_id=quiz.id,
    )
    db.add(document)
    db.flush()
    return document, quiz, questions


def get_or_create_quiz_user(db):
    """The app has no login (R2): all attempts share one anonymous user record."""
    from sql_alchemy import User

    user = db.query(User).filter(User.username == "anonymous").first()
    if user is None:
        user = User(
            username="anonymous",
            displayName="Quiz user",
            email="anonymous@quiz.local",
            role="user",
        )
        db.add(user)
        db.flush()
    return user


def load_question_ids(attempt) -> List[str]:
    try:
        ids = json.loads(attempt.selectedQuestionIds or "[]")
    except Exception:
        ids = []
    return [str(item) for item in ids if item]


def select_questions(db, quiz_id: str, order: str, count: int) -> List:
    """Pick the session's question subset in sequential or random order (R9-R10)."""
    from sql_alchemy import Question

    pool = (
        db.query(Question)
        .filter(Question.quiz_id == quiz_id)
        .order_by(Question.orderIndex.asc(), Question.id.asc())
        .all()
    )
    if order == "random":
        return random.sample(pool, count)
    return pool[:count]
