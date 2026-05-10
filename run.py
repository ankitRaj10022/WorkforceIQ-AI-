import os

from workforceiq import create_app

app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=bool(app.config.get("DEBUG", False)),
        use_reloader=bool(app.config.get("DEBUG", False)),
    )
