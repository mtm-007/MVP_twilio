import modal

app = modal.App("example-fasthtml")

@app.function(
    image=modal.Image.debian_slim(python_version="3.12").pip_install(
        "python-fasthtml==0.12.35"
    )
)
@modal.asgi_app()
def serve():
    import fasthtml.common as fh

    app = fh.FastHTML()

    @app.get('/')
    def home():
        return fh.Div(fh.P("Modal deployment first try!"), hx_get="/change")

    return app