from fulfilltwin.backend.app import create_app
from fulfilltwin.config import settings

app = create_app()

if __name__ == "__main__":
    app.run(host=settings.api_host, port=settings.api_port, debug=True)
