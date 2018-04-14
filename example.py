import celerystar as cs

class InitialState(cs.Type):
    init_int = cs.Integer()
    init_str = cs.String(allow_null=True)

class Component1(cs.Component):
    def resolve(self, state: InitialState) -> float:
        return float(state['init_int'])

class Component2(cs.Component):
    def resolve(self, state: InitialState) -> int:
        return int(state['init_str'])

def task1(value: float):
    "Sample task #1"
    return value + 0.1

def task2(value1: float, value2: int):
    "Sample task #2"
    return value1 * value2 + 0.1

app1 = cs.make_celery_app('teste1')
app2 = cs.make_celery_app('teste2', backend='redis://')

components = [Component1(), Component2()]
srv1 = cs.make_service(task1, components, InitialState, app1)
srv2 = cs.make_service(task2, components, InitialState, app1)
srv3 = cs.make_resulter_service(task2, components, InitialState, app2)
wsgi_app = cs.make_wsgi_app([srv2, srv1, srv3])


if __name__ == '__main__':
    wsgi_app.serve('127.0.0.1', 3000)