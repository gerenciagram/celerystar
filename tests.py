
from unittest.mock import MagicMock, patch
from contextlib import ExitStack, contextmanager
from functools import wraps

from pytest import raises

import celerystar as cs
from celerystar_apistar.test import TestClient


@contextmanager
def nested(*contexts):
    with ExitStack() as stack:
        yield [stack.enter_context(ctx) for ctx in contexts]


def dummy_impl():
        return 1


class ClassImpl:

    def run(self):
        return 1


class CallableImpl:

    def __call__(self):
        return 1


class InitialState(cs.Type):
        state1 = cs.Integer()


validation_dict = {
    'str': cs.String(max_length=2),
    'obj': cs.Object(properties={
        'uni': cs.Union(items=[
            cs.Integer(),
            cs.Number()
        ])
    }),
    'int': cs.Integer(),
}


make_base_build_task_patch = patch.object(cs.BaseService, '_build_task',
                                          create=True)


def make_resulter_mixin_build_task_patch(func):
    app = cs.Celery(backend='redis://')

    @patch.object(cs.ResulterMixin, 'app', app, create=True)
    @patch.object(cs.ResulterMixin, '_validate_apply_options', create=True)
    @patch.object(cs.ResulterMixin, 'data_cls', create=True)
    @patch.object(cs.ResulterMixin, 'task', create=True)
    @wraps(func)
    def wrapped(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapped()


def make_service_task_builder_mixin_patch(cls, impl):
    app = cs.Celery()
    injector = cs.Injector([], {})

    def decorator(func):
        @patch.object(cls, 'task_decorator', app.task, create=True)
        @patch.object(cls, 'injector', injector, create=True)
        @patch.object(cls, 'get_impl', lambda *_: impl, create=True)
        @wraps(func)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapped
    return decorator


def test_base_service_make_options_simple():
    opts = cs.BaseService._make_task_options(dummy_impl, {})
    assert opts == {
        'base': cs.Task,
        'name': 'dummy_impl',
    }


def test_base_service_make_options_with_name():
    opts = cs.BaseService._make_task_options(dummy_impl, {'name': 'task'})
    assert opts == {
        'base': cs.Task,
        'name': 'task',

    }


def test_base_service_make_options_with_options():
    opts = cs.BaseService._make_task_options(dummy_impl, {'opt1': 'value'})
    assert opts == {
        'base': cs.Task,
        'name': 'dummy_impl',
        'opt1': 'value'
    }


@make_base_build_task_patch
def test_base_service_repr(_):
    srv = cs.BaseService(cs.Celery(), cs.Injector([], {}), dummy_impl,
                         cs.Type(), {})
    srv._build_task = MagicMock()
    assert repr(srv) == 'Service<name=dummy_impl>'


@make_base_build_task_patch
def test_base_service_validate_celery_app(_):
    srv = cs.BaseService(cs.Celery(), cs.Injector([], {}), dummy_impl,
                         cs.Type(), {})
    with raises(cs.ConfigurationError, match="cannot handle result backends"):
        app = cs.Celery(backend='redis://')
        srv = cs.BaseService(app, cs.Injector([], {}), dummy_impl,
                             cs.Type(), {})


@make_base_build_task_patch
def test_base_service_validate_apply_options(_):
    with raises(cs.ConfigurationError, match="only json is supported"):
        cs.BaseService._validate_apply_options({'serializer': 'pickle'})


# @make_base_build_task_patch
# def test_base_service_validate_initial_state(_):
#     app = cs.Celery()
#     srv = cs.BaseService(app, cs.Injector([], {}), dummy_impl, {}, {
#         'int': cs.Integer()
#     })
#     srv._validate_initial_state({'int': 1})
#     with raises(cs.ValidationError):
#         srv._validate_initial_state({'int': 1.1})


@make_base_build_task_patch
def test_base_service_validate(_):
    with patch.object(cs.BaseService, '_validate') as func:
        srv = cs.BaseService(cs.Celery(), cs.Injector([], {}), dummy_impl,
                                    cs.Type(), {})
        func.assert_called()

    with raises(cs.ConfigurationError,
                match='No component able to handle parameter "param" on'
                      ' function "unresolvable".'):
        def unresolvable(param: int):
            return
        srv = cs.BaseService(cs.Celery(), cs.Injector([], {}), unresolvable,
                             cs.Type(), {})


@make_base_build_task_patch
def test_base_service_apply_local(build_task):
    build_task().apply().get.return_value = 2

    srv = cs.BaseService(cs.Celery(), cs.Injector([], {}), dummy_impl,
                            InitialState, {})
    initial_state = {'state1': 1}
    apply_opts = {'opt1': 1}

    assert srv.apply_local(initial_state, apply_opts) == 2
    srv.task.apply.assert_called_with([initial_state], {}, **apply_opts)


@make_base_build_task_patch
def test_base_service_apply_remote(_):
    srv = cs.BaseService(cs.Celery(), cs.Injector([], {}), dummy_impl,
                         InitialState, {})
    srv.task.apply_async = MagicMock()
    result_id = '3c5faf50-d500-446e-8f25-b0347695c9df'
    srv.task.apply_async().id = result_id

    initial_state = {'state1': 1}
    apply_opts = {'opt1': 1}

    res = srv.apply_remote(initial_state, apply_opts)
    srv.task.apply_async.assert_called_with([initial_state], {}, **apply_opts)


@make_base_build_task_patch
def test_resulter_mixin_validate_celery_app(self):
    app = cs.Celery()
    with patch.object(cs.ResulterMixin, 'app', app, create=True):
        with raises(cs.ConfigurationError,
                    match="a result backend is required"):
            srv = cs.ResulterMixin()
            srv._validate_celery_app()

    app = cs.Celery(backend='redis://')
    with patch.object(cs.ResulterMixin, 'app', app, create=True):
        srv = cs.ResulterMixin()
        srv._validate_celery_app()


@make_resulter_mixin_build_task_patch
def test_resulter_mixin_apply_remote(_a, _b, _c):
    srv = cs.ResulterMixin()

    initial_state = {'state1': int}
    apply_opts = {'opt1': 1}
    result_opts = {'timeout': 1}

    srv.task.apply_async().get.return_value = 2
    assert srv.apply_remote(initial_state, apply_opts, result_opts) == 2
    srv.task.apply_async.assert_called_with([initial_state], {},
                                            **apply_opts)
    srv.task.apply_async().get.assert_called_with(**result_opts)


@make_resulter_mixin_build_task_patch
def test_resuler_mixin_apply_error(_a, _b, c):
    srv = cs.ResulterMixin()

    initial_state = {}
    apply_opts = {}
    result_opts = {'timeout': 0}
    with raises(cs.ConfigurationError,
                match="timeout>0 is required to get results"):
        assert srv.apply_remote(initial_state, apply_opts, result_opts)


@make_service_task_builder_mixin_patch(cs.FunctionTaskBuilderMixin, dummy_impl)
def test_function_task_builder_mixin():
    srv = cs.FunctionTaskBuilderMixin()
    task = srv._build_task()
    assert task.apply([{}]).get() == 1


@make_service_task_builder_mixin_patch(cs.ClassTaskBuilderMixin, ClassImpl)
def test_class_task_builder_mixin():
    srv = cs.ClassTaskBuilderMixin()
    task = srv._build_task()
    assert task.apply([{}]).get() == 1


@make_service_task_builder_mixin_patch(cs.CallableTaskBuilderMixin,
                                       CallableImpl())
def test_callable_task_builder_mixin():
    srv = cs.CallableTaskBuilderMixin()
    task = srv._build_task()
    assert task.apply([{}]).get() == 1


def test_make_resulter_service():
    app = cs.Celery(backend='redis://')
    injector = cs.Injector([], {})

    srv = cs.make_resulter_service(dummy_impl, [], InitialState, app)
    assert isinstance(srv, cs.FunctionResulterService)

    srv = cs.make_resulter_service(ClassImpl, [], InitialState, app)
    assert isinstance(srv, cs.ClassResulterService)

    srv = cs.make_resulter_service(CallableImpl(), [], InitialState, app)
    assert isinstance(srv, cs.CallableResulterService)

    with raises(cs.ConfigurationError, match="1 could not be handled"):
        cs.make_resulter_service(1, injector, None, app)


def test_make_service():
    app = cs.Celery()

    srv = cs.make_service(dummy_impl, [], InitialState, app)
    assert isinstance(srv, cs.FunctionService)

    srv = cs.make_service(ClassImpl, [], InitialState, app)
    assert isinstance(srv, cs.ClassService)

    srv = cs.make_service(CallableImpl(), [], InitialState, app)
    assert isinstance(srv, cs.CallableService)

    with raises(cs.ConfigurationError, match="1 could not be handled"):
        cs.make_service(1, [], InitialState, app)


def test_make_injector():
    class Component(cs.Component):
        pass

    class InitialState(cs.Type):
        a_int = cs.Integer()
        a_obj = cs.Object()

    from celerystar.celerystar import _make_injector
    _make_injector([Component], InitialState)


def test_make_wsgi_app():

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

    app = cs.make_celery_app('test')

    components = [Component1(), Component2()]
    srv1 = cs.make_service(task1, components, InitialState, app)
    srv2 = cs.make_service(task2, components, InitialState, app)
    wsgi_app = cs.make_wsgi_app([srv2, srv1])

    client = TestClient(wsgi_app)

    ret = client.post('/test/task1', json={
        'apply_opts': {},
        'result_opts': {},
        'data': {
            'init_int': 1,
            'init_str': None
        }
    })
    assert ret.status_code == 200
    assert ret.json() == 1.1

    ret = client.post('/test/task2', json={
        'apply_opts': {},
        'result_opts': {},
        'data': {
            'init_int': 1,
            'init_str': '2'
        }
    })
    assert ret.status_code == 200
    assert ret.json() == 2.1

    srv1.task.apply_async = MagicMock()
    result_id = '3c5faf50-d500-446e-8f25-b0347695c9df'

    srv1.task.apply_async().id = result_id
    ret = client.post('/test/task1', json={
        'apply_opts': {},
        'result_opts': {},
        'remote': True,
        'data': {
            'init_int': 1,
            'init_str': None
        }
    })
    assert ret.status_code == 200
    assert ret.json() == result_id