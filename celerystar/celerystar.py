from os import path
from types import FunctionType
from typing import Callable, Dict, Any, List, Union as PythonUnion
from functools import wraps

from celerystar_apistar.server.injector import Injector, ConfigurationError
from celerystar_apistar.validators import Validator
from celerystar_apistar import Route, App
from celerystar_apistar.types import Type
from celerystar_apistar.http import JSONResponse, Response

from celery import Celery, Task as CeleryTask

from celerystar_apistar.server.components import Component
from celerystar_apistar.validators import (
    ValidationError,
    String, Number, Integer, Boolean, Object, Array, Date, Time, DateTime,
    Union, Uniqueness, Any
)


StrDict = Dict[str, Any]


class Task(CeleryTask):
    pass


class BaseService:
    """Service base class.

    @arg app Celery app instance
    @arg injector apistar injector instance
    @arg task_impl object implementing task
    @arg celery_task_opts Celery Task options

    """

    def __init__(self, app: Celery, injector: Injector, task_impl,
                 data_cls, celery_task_opts: StrDict) -> None:
        self.app = app
        self.injector = injector
        self.data_cls = data_cls
        self.get_impl = lambda *_: task_impl

        self.opts = self._make_task_options(task_impl, celery_task_opts)
        self.name = self.opts['name']
        self.task_decorator = app.task(**self.opts)

        self._validate()
        self.task = self._build_task()

    def __repr__(self):
        return f"Service<name={self.name}>"

    @staticmethod
    def _make_task_options(impl, opts: StrDict):
        opts['base'] = opts.get('base', Task)
        if 'name' not in opts:
            opts['name'] = impl.__name__
        return opts

    def _validate(self):
        self._validate_celery_app()
        self.injector.resolve_functions([self.get_impl()])

    def _validate_celery_app(self):
        if self.app.conf.result_backend:
            raise ConfigurationError("cannot handle result backends")

    @staticmethod
    def _validate_apply_options(opts: StrDict):
        if 'serializer' in opts and opts['serializer'] != 'json':
            raise ConfigurationError("only json is supported")

    def apply_local(self, initial_state: StrDict, apply_opts: StrDict) -> None:
        """Run service locally calling apply().

        @arg initial_state initial injection data
        @arg apply_opts kwargs provided to celery's apply()
        @throws ValidationError if initial_state is invalid
        @return result of the task

        """
        self.data_cls(initial_state)
        self._validate_apply_options(apply_opts)
        result = self.task.apply([initial_state], {}, **apply_opts)
        return result.get()

    def apply_remote(self, initial_state: StrDict,
                     apply_opts: StrDict) -> None:
        """Run service remotely calling apply_async().

        @arg initial_state initial injection data
        @arg apply_opts kwargs provided to celery's apply_async()
        @throws ValidationError if initial_state is invalid

        """
        self.data_cls(initial_state)
        self._validate_apply_options(apply_opts)
        result = self.task.apply_async([initial_state], {}, **apply_opts)
        return result.id


class ResulterMixin:

    def _validate_celery_app(self):
        if not self.app.conf.result_backend:
            raise ConfigurationError("a result backend is required")

    def apply_remote(self, initial_state: StrDict, apply_opts: StrDict,
                     result_opts: StrDict) -> Any:
        """Run service remotely calling apply_async().

        @arg initial_state initial injection data
        @arg apply_opts kwargs provided to celery's apply_async()
        @arg result_opts kwargs provided to celery's ResultBase.get()
        @throws ValidationError if initial_state is invalid
        @return restult of the task

        """
        self.data_cls(initial_state)
        self._validate_apply_options(apply_opts)
        if result_opts.get('timeout', -1) <= 0:
            raise ConfigurationError("timeout>0 is required to get results")
        result = self.task.apply_async([initial_state], {}, **apply_opts)
        return result.get(**result_opts)


class BaseTaskBuilderMixin:

    def _make_initial_state(self, data):
        return {'_hack_': data}


class FunctionTaskBuilderMixin(BaseTaskBuilderMixin):

    def _build_task(self) -> CeleryTask:
        @self.task_decorator
        def task(data):
            return self.injector.run([self.get_impl()],
                                     self._make_initial_state(data))
        return task


class ClassTaskBuilderMixin(BaseTaskBuilderMixin):

    def _build_task(self) -> CeleryTask:
        @self.task_decorator
        def task(data):
            obj = self.injector.run([self.get_impl()],
                                     self._make_initial_state(data))
            return obj.run()
        return task


class CallableTaskBuilderMixin(FunctionTaskBuilderMixin):

    @classmethod
    def _make_task_options(cls, impl: Callable, opts: StrDict):
        if 'name' not in opts:
            opts['name'] = impl.__class__.__name__
        return super()._make_task_options(impl, opts)


class FunctionService(FunctionTaskBuilderMixin, BaseService):
    """Function based Service."""


class FunctionResulterService(FunctionTaskBuilderMixin, ResulterMixin,
                              BaseService):
    """Function based Service that handles results."""


class ClassService(ClassTaskBuilderMixin, BaseService):
    """Class based Service."""


class ClassResulterService(ClassTaskBuilderMixin, ResulterMixin,
                           BaseService):
    """Class based Service that handles results."""


class CallableService(CallableTaskBuilderMixin, BaseService):
    """Callable object based Service."""


class CallableResulterService(CallableTaskBuilderMixin, ResulterMixin,
                              BaseService):
    """Callable object based Service that handles results."""


def make_resulter_service(impl: Callable, components: List[Component],
                          data_cls, app: Celery,
                          **celery_opts: StrDict) -> BaseService:
    if isinstance(impl, FunctionType):
        service_cls = FunctionResulterService
    elif isinstance(impl, type):
        service_cls = ClassResulterService
    elif callable(impl):
        service_cls = CallableResulterService
    else:
        raise ConfigurationError(f"{impl} could not be handled")
    injector = _make_injector(components, data_cls)
    return service_cls(app, injector, impl, data_cls,
                       celery_opts)


def make_service(impl: Callable, components: List[Component],
                 data_cls, app: Celery,
                 **celery_opts: StrDict) -> BaseService:
    if isinstance(impl, FunctionType):
        service_cls = FunctionService
    elif isinstance(impl, type):
        service_cls = ClassService
    elif callable(impl):
        service_cls = CallableService
    else:
        raise ConfigurationError(f"{impl} could not be handled")
    injector = _make_injector(components, data_cls)
    return service_cls(app, injector, impl, data_cls,
                       celery_opts)


def make_celery_app(name: str, **opts: StrDict) -> Celery:
    return Celery(
        **opts,
        main=name,
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
    )


def _make_injector(components: List[Component],
                   data_cls: Type) -> Injector:
    class InitialState(Type):
        _hack_ = data_cls

    class InitialComponent(Component):
        def resolve(self, state: InitialState) -> data_cls:
            return data_cls(state['_hack_'])

    return Injector([InitialComponent(), *components],
                    {'_hack_': data_cls})


def _make_view(service: BaseService, post_data_cls: Type) -> Callable:
    def view(post_data: post_data_cls):
        if post_data['remote']:
            if isinstance(service, ResulterMixin):
                response = service.apply_remote(post_data['data'],
                                                post_data['apply_opts'],
                                                post_data['result_opts'])
            else:
                response = service.apply_remote(post_data['data'],
                                                post_data['apply_opts'])
        else:
            response = service.apply_local(post_data['data'],
                                           post_data['apply_opts'])
        return JSONResponse(response)
    return view


def make_wsgi_app(services: List[BaseService]):
    routes = []
    for srv in services:
        post_data_cls = type(f'{srv.name}_PostData', (Type,), {
            'apply_opts': Object(),
            'result_opts': Object(),
            'remote': Boolean(default=False),
            'data': Object(
                properties=srv.data_cls.validator.properties,
                required=list(srv.data_cls.validator.properties),
                additional_properties=False,
            ),
        })
        routes.append(Route(f'/{srv.app.main}/{srv.name}', 'POST',
                            handler=_make_view(srv, post_data_cls),
                            name=f'{srv.app.main}/{srv.name}'))
    def index():
        return Response('', status_code=302,
                        headers={'Location': '/static/index.html'},)
    routes.append(Route('/', 'GET', handler=index, documented=False))
    static_dir = path.join(path.dirname(__file__), 'static')
    return App(
        routes=routes,
        static_dir=static_dir
    )
