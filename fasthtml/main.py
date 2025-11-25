from fasthtml.common import *

def render(todo):
    tid = f'todo-{todo.id}'
    toggle = A('Toggle', hx_get=f'/toggle/{todo.id}', target_id=tid)
    delete = A('Delete', hx_delete=f'/{todo.id}',
               hx_swap='outerHTML', target_id=tid)
    return Li(toggle, delete, todo.title + (' ✅' if todo.done else ''),
              id=tid)

app, rt, todos, Todo = fast_app(
        'data/todos.db',
        tbls={"todos":dict(id=int, title=str, render=render, done=bool, pk='id')})

def mk_input(): return Input(placeholder='Add a new todo', id='title', hx_swap_oob='true')

@rt('/')
def get():
    frm = Form(Group(mk_input(), 
                     Button("Add")),
               hx_post='/', target_id='todo-list', hx_swap='beforeend')
    return Titled('Todos List',
                  Card(
                        Ul(*todos(), id='todo-list'),
                        header=frm)
                  )

@rt('/')
def post(todo:Todo): return todos.insert(todo), mk_input()

@rt('/{tid}')
def delete(tid:int):todos.delete(tid)

@rt('/toggle/{tid}')
def get(tid:int):
    todo = todos[tid]
    todo.done = not todo.done
    return todos.update(todo)

serve()
