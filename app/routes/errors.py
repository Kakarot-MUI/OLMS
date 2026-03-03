from flask import Blueprint, render_template

errors_bp = Blueprint('errors', __name__)


@errors_bp.app_errorhandler(403)
def forbidden(error):
    """Custom 403 Forbidden page."""
    return render_template('errors/403.html'), 403


@errors_bp.app_errorhandler(404)
def not_found(error):
    """Custom 404 Not Found page."""
    return render_template('errors/404.html'), 404


@errors_bp.app_errorhandler(500)
def internal_error(error):
    """Custom 500 Internal Server Error page."""
    return render_template('errors/500.html'), 500
