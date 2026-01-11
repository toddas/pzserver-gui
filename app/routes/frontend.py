from flask import Blueprint, render_template, send_from_directory, current_app, abort

frontend_bp = Blueprint('frontend', __name__)

@frontend_bp.route('/')
def serve_dashboard():
    return render_template('index.html')

@frontend_bp.route('/mods')
def serve_mods():
    return render_template('mods.html')

@frontend_bp.route('/sandbox')
def serve_sandbox():
    return render_template('sandbox.html')

@frontend_bp.route('/config')
def serve_config():
    return render_template('config.html')

# Serve favicon
@frontend_bp.route('/favicon.ico')
def favicon():
    return send_from_directory(current_app.static_folder, 'favicon.ico', mimetype='image/x-icon')
