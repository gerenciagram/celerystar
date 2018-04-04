from apistar.server.components import Component
from apistar.server.injector import Injector


def t1(a_int: int, a_str: str):
    return f't1: {type(a_int)}:{repr(a_int)}_{type(a_str)}:{repr(a_str)}'


def t2(a_int: int):
    return f't2: {type(a_int)}:{repr(a_int)}'


class IntComponent(Component):

    def resolve(self, stream: bytes) -> int:
        return int(stream.decode())


class StrComponent(Component):

    def resolve(self, stream: bytes) -> str:
        return str(stream.decode())


injector = Injector(
    [IntComponent(), StrComponent()],
    {'stream': bytes}
)

r1 = injector.run([t1], {'stream': b'1'})
r2 = injector.run([t2], {'stream': b'2'})

print(r1)
print(r2)
