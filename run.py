import os
import sys

# Ensure the project root is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.logger.info("Starting PZ Server Manager API...")
    app.run(host='0.0.0.0', port=5000, debug=True)
