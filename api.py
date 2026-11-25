
import os

from flask import Flask, request, jsonify, render_template
from processing import command_analyzer

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "engine": "PythonSQL"
    })


@app.route("/api/query", methods=["POST"])
def execute_query():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "error": "Invalid request."
        }), 400

    query = data.get("query")

    if not isinstance(query, str) or not query.strip():
        return jsonify({
            "success": False,
            "error": "Please enter a SQL query."
        }), 400

    query = query.strip()

    if len(query) > 5000:
        return jsonify({
            "success": False,
            "error": "Query is too long."
        }), 400

    try:
        result = command_analyzer(query)
        output = str(result)

        if output.strip().upper().startswith("ERROR"):
            return jsonify({
                "success": False,
                "error": output
            }), 400

        return jsonify({
            "success": True,
            "result": output
        })

    except Exception:
        app.logger.exception("Query execution failed")

        return jsonify({
            "success": False,
            "error": "Unable to execute query."
        }), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
