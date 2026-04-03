from flask import Blueprint, render_template
import traceback

errors_bp = Blueprint('errors', __name__)

@errors_bp.app_errorhandler(403)
def forbidden(error):
    """Custom 403 Forbidden page."""
    return render_template('errors/403.html'), 403

@errors_bp.app_errorhandler(404)
def not_found(error):
    """Custom 404 Not Found page."""
    return render_template('errors/404.html'), 404

@errors_bp.app_errorhandler(Exception)
def handle_exception(e):
    """Catch all exceptions and show the traceback for debugging."""
    return f"<h1>500 Internal Server Error</h1><pre>{traceback.format_exc()}</pre>", 500
