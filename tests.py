
from unittest.mock import MagicMock, patch
from pytest import raises
from contextlib import ExitStack, contextmanager
from functools import wraps

import celerystar as cs


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


base_build_task_patch = patch.object(cs.BaseService, '_build_task',
                                     create=True)


def make_resulter_mixin_build_task_patch(func):
    app = cs.Celery(backend='redis://')

    @patch.object(cs.ResulterMixin, 'app', app, create=True)
    @patch.object(cs.ResulterMixin, '_validate_apply_options', create=True)
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


@base_build_task_patch
def test_base_service_repr(_):
    srv = cs.BaseService(cs.Celery(), cs.Injector([], {}), dummy_impl, {})
    srv._build_task = MagicMock()
    assert repr(srv) == 'Service<name=dummy_impl>'


@base_build_task_patch
def test_base_service_validate_celery_app(_):
    cs.BaseService(cs.Celery(), cs.Injector([], {}), dummy_impl, {})
    with raises(cs.ConfigurationError, match="cannot handle result backends"):
        app = cs.Celery(backend='redis://')
        cs.BaseService(app, cs.Injector([], {}), dummy_impl, {})


@base_build_task_patch
def test_base_service_validate_apply_options(_):
    with raises(cs.ConfigurationError, match="only json is supported"):
        cs.BaseService._validate_apply_options({'serializer': 'pickle'})


@base_build_task_patch
def test_base_service_validate(_):
    with patch.object(cs.BaseService, '_validate') as func:
        cs.BaseService(cs.Celery(), cs.Injector([], {}), dummy_impl, {})
        func.assert_called()

    with raises(cs.ConfigurationError,
                match='No component able to handle parameter "param" on'
                      ' function "unresolvable".'):
        def unresolvable(param: int):
            return
        cs.BaseService(cs.Celery(), cs.Injector([], {}), unresolvable, {})


@base_build_task_patch
def test_base_service_apply_local(build_task):
    build_task().apply().get.return_value = 2

    srv = cs.BaseService(cs.Celery(), cs.Injector([], {}), dummy_impl, {})
    initial_state = {'state1': int}
    apply_opts = {'opt1': 1}

    assert srv.apply_local(initial_state, apply_opts) == 2
    srv.task.apply.assert_called_with([initial_state], {}, **apply_opts)


@base_build_task_patch
def test_base_service_apply_remote(_):
    srv = cs.BaseService(cs.Celery(), cs.Injector([], {}), dummy_impl, {})
    initial_state = {'state1': int}
    apply_opts = {'opt1': 1}

    assert srv.apply_remote(initial_state, apply_opts) is None
    srv.task.apply_async.assert_called_with([initial_state], {}, **apply_opts)


@base_build_task_patch
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
def test_resulter_mixin_apply_remote(_a, _b):
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
def test_resuler_mixin_apply_error(_a, _b):
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

    srv = cs.make_resulter_service(dummy_impl, injector, app)
    assert isinstance(srv, cs.FunctionResulterService)

    srv = cs.make_resulter_service(ClassImpl, injector, app)
    assert isinstance(srv, cs.ClassResulterService)

    srv = cs.make_resulter_service(CallableImpl(), injector, app)
    assert isinstance(srv, cs.CallableResulterService)

    with raises(cs.ConfigurationError, match="1 could not be handled"):
        cs.make_resulter_service(1, injector, app)


def test_make_resulter_service():
    app = cs.Celery()
    injector = cs.Injector([], {})

    srv = cs.make_service(dummy_impl, injector, app)
    assert isinstance(srv, cs.FunctionService)

    srv = cs.make_service(ClassImpl, injector, app)
    assert isinstance(srv, cs.ClassService)

    srv = cs.make_service(CallableImpl(), injector, app)
    assert isinstance(srv, cs.CallableService)

    with raises(cs.ConfigurationError, match="1 could not be handled"):
        cs.make_service(1, injector, app)
