import os
from app import create_app

config_name = os.environ.get('FLASK_ENV', 'production')
app = create_app(config_name)
