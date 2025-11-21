from fasthtml.common import *
#from fasthtml import common as fh


app, rt = fast_app(live=True)

def numList(i):
    return Ul(*[Li(o)for o in range(i)])

@rt('/')
def get():
    nums = numList(5)
    return Titled('Greeting'
                  ,Div(P("FIrst FastHtml webpage with python !")),
                  Div(nums, id="stuff", hx_get='/repo'),
                  )

@rt('/repo')
def get():
    return P('Repo link here.')

serve()
