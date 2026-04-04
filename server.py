"""Flask-based validation server for the Digitad OPG web validation UI.

The ValidationServer manages a local Flask server running in a daemon thread,
serves HTML templates for onboarding/mapping/progress pages, provides JSON API
endpoints, and syncs with the CLI via threading.Event so the CLI blocks until
the consultant validates in the browser.
"""
import socket
import threading
import time
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request


class ValidationServer:
    """Local Flask server for browser-based keyword mapping validation.

    The CLI creates an instance, calls start(), opens the browser, then calls
    wait_for_validation() which blocks until the consultant submits the form.
    The validated/modified mapping is returned as server.result.
    """

    def __init__(
        self,
        mapping_data: Dict[str, Any],
        opp_scores: Dict[str, float],
        config: Dict[str, Any],
    ) -> None:
        self.mapping_data = mapping_data
        self.opp_scores = opp_scores
        self.config = config

        self.result: Optional[Dict[str, Any]] = None
        self.ready_event = threading.Event()

        self._lock = threading.Lock()
        self._progress: Dict[str, Any] = {
            "step": None,
            "current": 0,
            "total": 0,
            "done": False,
        }
        self._validated = False
        self._server_thread: Optional[threading.Thread] = None
        self._flask_server = None
        self.port: Optional[int] = None

    # ------------------------------------------------------------------
    # Public data helpers
    # ------------------------------------------------------------------

    def format_api_data(self) -> Dict[str, Any]:
        """Return a serialisable dict grouping URLs by language for the UI."""
        by_lang: Dict[str, List[Dict[str, Any]]] = {}

        for url, entry in self.mapping_data.items():
            lang = entry.get("lang", "unknown")
            row = {
                "url": url,
                "keyword": entry.get("keyword"),
                "similarity": entry.get("similarity"),
                "volume": entry.get("volume"),
                "position": entry.get("position"),
                "relevance_score": entry.get("relevance_score"),
                "confidence": entry.get("confidence"),
                "top_queries": entry.get("top_queries", []),
                "opportunity_score": self.opp_scores.get(url),
            }
            by_lang.setdefault(lang, []).append(row)

        return {
            "client": self.config,
            "mapping": by_lang,
        }

    def apply_validation_result(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge consultant edits back into the original mapping.

        Entries with status "skip" are excluded from the result.

        Raises:
            ValueError: when the resulting mapping would be empty.
        """
        raw = post_data.get("mapping", {})
        result: dict[str, Any] = {}

        for url, edits in raw.items():
            status = edits.get("status", "ok")
            if status == "skip":
                continue
            # Start from original entry and overlay consultant edits.
            merged = dict(self.mapping_data.get(url, {}))
            merged.update({k: v for k, v in edits.items() if k != "status"})
            result[url] = merged

        if not result:
            raise ValueError("Validation result is empty - at least one URL must be accepted.")

        return result

    # ------------------------------------------------------------------
    # Progress tracking (thread-safe)
    # ------------------------------------------------------------------

    def update_progress(self, step: str, current: int, total: int) -> None:
        with self._lock:
            self._progress.update({"step": step, "current": current, "total": total, "done": False})

    def complete_step(self, step: str) -> None:
        with self._lock:
            self._progress.update({"step": step, "done": False})

    def mark_done(self, grace_seconds: float = 2.0) -> None:
        """Mark progress as done, optionally waiting before flagging."""
        if grace_seconds > 0:
            time.sleep(grace_seconds)
        with self._lock:
            self._progress["done"] = True

    def get_progress(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._progress)

    # ------------------------------------------------------------------
    # Flask app factory
    # ------------------------------------------------------------------

    def _create_app(self) -> Flask:
        app = Flask(__name__, template_folder="templates")
        # Prevent Jinja from caching in dev/test mode
        app.config["TEMPLATES_AUTO_RELOAD"] = True

        server_ref = self  # closure reference

        # ---- HTML routes (templates provided by Tasks 3-5) ----

        @app.route("/")
        def onboarding():
            return render_template("onboarding.html", config=server_ref.config)

        @app.route("/mapping")
        def mapping():
            return render_template("mapping.html", config=server_ref.config)

        @app.route("/progress")
        def progress_page():
            return render_template("progress.html", config=server_ref.config)

        # ---- JSON API routes ----

        @app.get("/api/data")
        def api_data():
            return jsonify(server_ref.format_api_data())

        @app.post("/api/validate")
        def api_validate():
            if server_ref._validated:
                return jsonify({"error": "Validation already submitted."}), 409

            payload = request.get_json(force=True, silent=True) or {}
            try:
                result = server_ref.apply_validation_result(payload)
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400

            server_ref.result = result
            server_ref._validated = True
            server_ref.ready_event.set()
            return jsonify({"ok": True, "accepted": len(result)})

        @app.get("/api/progress")
        def api_progress():
            return jsonify(server_ref.get_progress())

        return app

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    def _find_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def start(self) -> int:
        """Start the Flask server in a daemon thread and return the port."""
        from werkzeug.serving import make_server

        self.port = self._find_free_port()
        app = self._create_app()

        self._flask_server = make_server("127.0.0.1", self.port, app)

        self._server_thread = threading.Thread(
            target=self._flask_server.serve_forever,
            daemon=True,
            name="validation-server",
        )
        self._server_thread.start()
        return self.port

    def wait_for_validation(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Block until the consultant submits the form (or timeout expires).

        Returns:
            The validated mapping dict, or None on timeout.
        """
        self.ready_event.wait(timeout=timeout)
        return self.result

    def shutdown(self) -> None:
        """Stop the Flask server if running."""
        if self._flask_server is not None:
            self._flask_server.shutdown()
            self._flask_server = None
