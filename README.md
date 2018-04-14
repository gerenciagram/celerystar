# CeleryStar

CeleryStar provides APIStar dependency injection mechanism to Celery. It has many benefits:

* simplified task creation
* data validation
* HTTP interface to posting messages
* OpenAPI 3 interface & Swagger-UI
* many APIStar components

# Usage


```python
    import celerystar as cs

    # Components
    class BoolComponent(Component):

        def resolve(self, value: int) -> bool:
            return bool(value)

    # Describe initial data for service
    initial_state1 = {'init': int}
    state_validation_dict1 = {'init': Integer()}

    injector1 = Injector(
        [Component1()],
        initial_state1
    )
    app1 = make_celery_app('teste', backend='redis://')


    def task1(value: bool):
        "Sample task #1"
        return value

    # ResulterService has the capability of wait for task results
    srv1 = make_resulter_service(task1, injector1, state_validation_dict1, app1)

    srv1.apply_local({})

    class Component2(Component):

        def resolve(self, value: str) -> float:
            return float(value)


    srv2 = make_resulter_service(task2, injector1, state_validation_dict1, app1)


    initial_state2 = {'init': str}
    state_validation_dict2 = {'init': String()}
    injector2 = Injector(
        [Component2()],
        initial_state2
    )
    app2 = make_celery_app('teste')

    class Task3:

        def __init__(self, value: float):
            self.value = value

        def run(self):
            return self.value

    srv3 = make_service(Task3, injector2, state_validation_dict2, app2)



    if __name__ == '__main__':

        wsgi = make_wsgi_app([srv1, srv2, srv3])
        wsgi.serve('127.0.0.1', 5000)


```