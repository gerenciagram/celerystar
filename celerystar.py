from types import FunctionType
from typing import Callable, Dict, Any

from apistar.server.injector import Injector, ConfigurationError
from celery import Celery, Task as CeleryTask


StrDict = Dict[str, Any]


class Task(CeleryTask):

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        print(exc)


class BaseService:
    """Service base class.

    @arg app Celery app instance
    @arg injector APIStar injector instance
    @arg task_impl object implementing task
    @arg celery_task_opts Celery Task options

    """
    def __init__(self, app: Celery, injector: Injector, task_impl,
                 celery_task_opts: StrDict) -> None:
        self.app = app
        self.injector = injector
        self.get_impl = lambda *_: task_impl

        self.opts = self._make_task_options(task_impl, celery_task_opts)
        self.task_decorator = app.task(**self.opts)

        self._validate()
        self.task = self._build_task()

    def __repr__(self):
        return f"Service<name={self.opts['name']}>"

    @staticmethod
    def _make_task_options(impl, opts: StrDict):
        opts['base'] = opts.get('base', Task)
        if 'name' not in opts:
            opts['name'] = impl.__name__
        return opts

    def _validate(self):
        self._validate_celery_app()
        # throws ConfigurationError if impl parameters aren't resolvable
        self.injector.resolve_function(self.get_impl())

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
        @return result of the task

        """
        self._validate_apply_options(apply_opts)
        result = self.task.apply([initial_state], {}, **apply_opts)
        return result.get()

    def apply_remote(self, initial_state: StrDict,
                     apply_opts: StrDict) -> None:
        """Run service remotely calling apply_async().

        @arg initial_state initial injection data
        @arg apply_opts kwargs provided to celery's apply_async()

        """
        self._validate_apply_options(apply_opts)
        self.task.apply_async([initial_state], {}, **apply_opts)


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
        @return restult of the task

        """
        self._validate_apply_options(apply_opts)
        if result_opts.get('timeout', -1) <= 0:
            raise ConfigurationError("timeout>0 is required to get results")
        result = self.task.apply_async([initial_state], {}, **apply_opts)
        return result.get(**result_opts)


class FunctionTaskBuilderMixin:

    def _build_task(self) -> CeleryTask:
        @self.task_decorator
        def task(initial_state):
            return self.injector.run([self.get_impl()], initial_state)
        return task


class ClassTaskBuilderMixin:

    def _build_task(self) -> CeleryTask:
        @self.task_decorator
        def task(initial_state):
            obj = self.injector.run([self.get_impl()], initial_state)
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
    """Callable object based Service. """


class CallableResulterService(CallableTaskBuilderMixin, ResulterMixin,
                              BaseService):
    """Callable object based Service that handles results. """


def make_resulter_service(impl: Callable, injector: Injector, app: Celery,
                          **celery_opts: StrDict) -> BaseService:
    if isinstance(impl, FunctionType):
        service_cls = FunctionResulterService
    elif isinstance(impl, type):
        service_cls = ClassResulterService
    elif callable(impl):
        service_cls = CallableResulterService
    else:
        raise ConfigurationError(f"{impl} could not be handled")
    return service_cls(app, injector, impl, celery_opts)


def make_service(impl: Callable, injector: Injector, app: Celery,
                 **celery_opts: StrDict) -> BaseService:
    if isinstance(impl, FunctionType):
        service_cls = FunctionService
    elif isinstance(impl, type):
        service_cls = ClassService
    elif callable(impl):
        service_cls = CallableService
    else:
        raise ConfigurationError(f"{impl} could not be handled")
    return service_cls(app, injector, impl, celery_opts)


def make_celery_app(name: str, **opts: StrDict) -> Celery:
    return Celery(
        **opts,
        main=name,
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
    )
