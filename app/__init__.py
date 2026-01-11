import logging
import os
from flask import Flask

def create_app():
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')

    app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-please-change')

    # Configure Logging
    logger = logging.getLogger('pzserver_api')
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(ch)

    # Register Blueprints
    from app.routes.frontend import frontend_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(frontend_bp)
    app.register_blueprint(api_bp)

    return app
