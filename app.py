"""Навчальний Flask-застосунок із Gemini API: генератор ідей стартапів."""
import json
import os
import time

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)
TOPICS = {"education": "освіта", "health": "здоров’я", "games": "ігри"}


def generate_idea(topic):
    """Звертається до справжньої моделі Gemini; ключ читається лише з ENV."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Не задано GEMINI_API_KEY. Дивись README.md.")

    from google import genai
    from google.genai import types
    from google.genai.errors import ServerError

    prompt = (
        "Ти консультант із креативних стартапів. Придумай одну конкретну "
        f"ідею на тему «{topic}». Відповідай українською. "
        "Не вигадуй статистики чи доведених результатів. "
        "Поверни JSON з такими полями: "
        "name (назва до 5 слів), "
        "idea (опис продукту, 2–3 речення), "
        "slogan (короткий слоган)."
    )
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    client = genai.Client(api_key=api_key)

    # Тимчасове перевантаження Gemini (503): максимум 2 спроби.
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json", temperature=0.9
                ),
            )
            break
        except ServerError as exc:
            if getattr(exc, "code", None) == 503 and attempt == 0:
                time.sleep(2)
                continue
            raise

    if not response.text:
        raise ValueError("Модель повернула порожню відповідь.")
    data = json.loads(response.text)
    if not isinstance(data, dict) or not all(
        isinstance(data.get(key), str) and data[key].strip()
        for key in ("name", "idea", "slogan")
    ):
        raise ValueError("Модель повернула неправильний формат.")
    return {key: data[key].strip()[:900] for key in ("name", "idea", "slogan")}


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/generate")
def generate():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get("topic") not in TOPICS:
        return jsonify(error="Оберіть одну з доступних тем."), 400
    try:
        result = generate_idea(TOPICS[data["topic"]])
    except RuntimeError as exc:
        return jsonify(error=str(exc)), 503
    except Exception as exc:
        # У публічний відгук не віддаємо службових деталей чи ключа.
        code = getattr(exc, "code", None)
        app.logger.error("Gemini API error: %s (code=%s)", type(exc).__name__, code)
        if code == 503:
            return jsonify(error="Gemini тимчасово перевантажений. Спробуйте ще раз."), 503
        if code == 429:
            return jsonify(error="Квоту Gemini вичерпано. Спробуйте пізніше."), 503
        return jsonify(error="Не вдалося створити ідею. Перевір API-ключ і модель."), 502
    return jsonify(result)


if __name__ == "__main__":
    # Для локальної роботи на Windows. На Render запускає Gunicorn.
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "5000")), debug=False)
