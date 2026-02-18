from snakevortex import create_app
from snakevortex.config import SERVER_HOST, SERVER_PORT

app = create_app()


if __name__ == "__main__":
    app.run(host=SERVER_HOST, port=SERVER_PORT, debug=False)
