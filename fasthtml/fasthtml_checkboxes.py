import time
from asyncio import Lock
from pathlib import Path
from uuid import uuid4
import modal
import fasthtml.common as fh
import inflect

from .constants import N_CHECKBOXES

app = modal.App("fasthtml-checkboxes")
db = modal.Dict.from_name("fasthtml-checkboxes-db", create_if_missing=True)

css_path_local = Path(__file__).parent / "style.css"
css_path_remote = "assets/styles.css"

@app.function(
    image = modal.Image.debian_slim(python_version="3.12")
    .uv_pip_install("python-fasthtml==0.12.35", "inflect~=7.4.0"),
    concurrency_limit=1,#currently maintain state in memory, so we restrict the server to one worker
    mounts = [
        modal.Mount.from_local_file(css_path_local,remote_path=css_path_remote)
    ],
    allow_concurrent_inputs=1000,
)
#     .add_local_file(css_path_local,remote_path=css_path_remote),
#     max_containers=1,
# )

#@modal.concurrent(max_inputs=100)
@modal.asgi_app()
def web():
    #connected clients are tracked in memory
    clients = {}
    clients_mutex = Lock()

    checkboxes = db.get("checkboxes", [])
    checkboxes_mutex = Lock()

    if len(checkboxes) == N_CHECKBOXES:
        print("Restored checkboxes state from previous session.")
    else:
        print("Initializing checkbox state.")
        checkboxes =[]
        for i in range(N_CHECKBOXES):
            checkboxes.append(
                fh.Input(
                    id=f"cb-{i}",
                    type="checkbox",
                    checked=False,
                    # when clicked, that checkbox will send a POST request to the server with its index
                    hx_post=f"/checkbox/toggle/{i}",
                    hx_swap_oob="true",# allows us to later push diffs to arbitrary checkboxes by id
                )
            )
    async def on_shutdown():
        # Handle the shutdown event by persisting current state to modal dict
        async with checkboxes_mutex:
            db["checkboxes"]=checkboxes
        print("checkbox state persisted.")
    
    style= open(css_path_remote, "r").read()
    app, _ = fh.fast_app(
        on_shutdown=[on_shutdown],
        hdrs=[fh.Style(style)],
    )
    @app.get("/")
    async def get():
        client = Client()
        async with  clients_mutex:
            clients[client.id] =client
        return(
            fh.Titled(f"{N_CHECKBOXES // 1000}k Checkboxes"),
            fh.Main(
                fh.H1(
                    f"{inflect.engine().number_to_words(N_CHECKBOXES).title()} Checkboxes"
                ),
                fh.Div(
                    *checkboxes,
                    id="checkbox-array",
                ),
                cls="container",
                # use HTMX to poll for diffs to apply
                hx_trigger="every 1s", #poll every second
                hx_get=f"/diffs/{client.id}", #call the diffs  endpoint
                hx_swap="none"#dont replace the entire page
            ),
        )
    
    #users submitting checkbox toggles
    @app.post("checkbox/toggle/{i}")
    async def toggle(i:int):
        async with checkboxes_mutex:
            cb = checkboxes[i]
            cb.checked = not cb.checked
            checkboxes[i]=cb
        
        async with clients_mutex:
            expired = []
            for client in clients.values():
                #clean up old clients
                if not client.is_active():
                    expired.append(client.id)
                
                #add diff to client fpr when they next poll
                client.add_diff(i)

            for client_id in expired:
                del clients[client_id]
        return
    
    #clients polling for outstanding diffs
    @app.get("diffs/{client_id}")
    async def diffs(client_id:str):
        # we use the `hx_swap_oob='true'` feature to
        # push updates only for the checkboxes that changed
        async with clients_mutex:
            client = clients.get(client_id, None)
            if client is None or len(client.diffs) == 0:
                return
            
            client.heartburn()
            diffs = client.pull_diffs()

        async with checkboxes_mutex:
            diff_array = [checkboxes[i] for i in diffs]
        return diff_array
    
    return app

class Client:
    def __init__(self):
        self.id = str(uuid4())
        self.diffs = []
        self.inactive_deadline = time.time() + 30
    
    def is_active(self):
        return time.time() < self.inactive_deadline
    
    def heartbeat(self):
        self.inactive_deadline = time.time() + 30

    def add_diff(self, i):
        if i not in self.diffs:
            self.diffs.append(i)

    def pull_diffs(self):
        #return a copy of the diffs and clear them
        diffs = self.diffs
        self.diffs=[]
        return diffs