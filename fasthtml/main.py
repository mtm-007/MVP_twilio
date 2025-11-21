from fasthtml.common import *
#from fasthtml import common as fh


app, rt, todos, TodoList = fast_app('todos.db',live=True, 
                                id=int, title=str, done=bool, pk='id')

@rt('/')
def get():
    #todos.insert(TodoList(title='Second todo', done=False))
    items = [Li(o) for o in todos()]
    return Titled('Todos List',
                  Ul(*items),
                  )

serve()
