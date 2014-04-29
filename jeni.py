# jeni.py
# Copyright 2013-2014 Ron DuPlain <ron.duplain@gmail.com> (see AUTHORS file).
# Released under the BSD License (see LICENSE file).

"""jeni: dependency injection through annotations (dip)."""

__version__ = '0.3-dev'

import abc
import functools
import inspect
import re

import six


# Provide sentinel object that indicates a dependency cannot be fulfilled.

class Unset(object):
    """Alternative to None, and None may be a properly provided value."""
    __slots__ = ()

    def __nonzero__(self):
        return False


UNSET = Unset()


class UnsetError(KeyError):
    """Note could possibly be provided, but is currently unset."""
    def __init__(self, note, *a, **kw):
        self.note = note
        super(UnsetError, self).__init__(*a, **kw)


# Motivation: dependency injection using prepared providers.

@six.add_metaclass(abc.ABCMeta)
class Provider(object):
    @abc.abstractproperty
    def provide(self):
        return

    @abc.abstractmethod
    def get(self, name=None):
        return

    def close(self):
        return


class Injector(object):
    """Collects dependencies and reads annotations to fulfill them."""
    provider_registry = {} # registry: {class: {note: provider_or_fn}}
    re_note = re.compile(r'([^:]*):?(.*)') # annotation format: 'object:name'

    def __init__(self):
        self.instances = {}

    @classmethod
    def register(cls, *provider_seq):
        if cls not in cls.provider_registry:
            cls.provider_registry[cls] = {}
        for provider in provider_seq:
            cls.provider_registry[cls][provider.provide] = provider
        if len(provider_seq) > 0:
            # Support use as a decorator.
            return provider_seq[0]

    @classmethod
    def factory(cls, note, fn=None, generator=False):
        if cls not in cls.provider_registry:
            cls.provider_registry[cls] = {}
        def decorator(f):
            if generator:
                provider = cls.generator_to_provider(note, f)
                cls.provider_registry[cls][note] = provider
            else:
                cls.provider_registry[cls][note] = f
            return f
        if fn is None:
            return decorator
        return decorator(fn)

    @classmethod
    def generator(cls, note, fn=None):
        return cls.factory(note, fn=fn, generator=True)

    @classmethod
    def unregister(cls, note):
        cls.provider_registry[cls].pop(note)
        if not cls.provider_registry[cls]:
            cls.provider_registry.pop(cls)

    def apply(self, fn):
        notes, keyword_notes = collect_notes(fn)
        args, kwargs = self.fulfill(*notes, **keyword_notes)
        return fn(*args, **kwargs)

    def partial(self, fn):
        notes, keyword_notes = collect_notes(fn)
        args, kwargs = self.fulfill(*notes, **keyword_notes)
        return functools.partial(fn, *args, **kwargs)

    def fulfill(self, *notes, **keyword_notes):
        """Fulfill injection during function application."""
        args = tuple(self.resolve(note) for note in notes)
        kwargs = {k: self.resolve(v) for k, v in keyword_notes.items()}
        for arg, note in zip(args, notes):
            if arg is UNSET:
                msg = "{!r} is unable to provide '{}'.".format(self, note)
                raise UnsetError(note, msg)
        kwargs = {k: v for k, v in kwargs.items() if v is not UNSET}
        return args, kwargs

    def resolve(self, note):
        """Resolve a single note into an object."""
        basenote, name = self.parse_note(note)
        try:
            provider_or_fn = self.lookup(basenote)
        except LookupError:
            msg = "Unable to resolve '{}'"
            raise LookupError(msg.format(note))
        return self.handle_provider(provider_or_fn, basenote, name=name)

    def handle_provider(self, provider_or_fn, basenote, name=None):
        if inspect.isclass(provider_or_fn):
            if basenote in self.instances:
                provider_or_fn = self.instances[basenote]
            else:
                provider_or_fn = provider_or_fn()
                self.instances[basenote] = provider_or_fn
        if hasattr(provider_or_fn, 'get'):
            fn = provider_or_fn.get
        else:
            fn = provider_or_fn
        if has_annotations(fn):
            fn = self.partial(fn)
        if name is not None:
            return fn(name=name)
        return fn()

    def parse_note(self, note):
        """Parse string annotation into object reference with optional name."""
        try:
            match = self.re_note.match(note)
        except TypeError:
            # Note is not a string. Support any Python object as a note.
            return note, None
        return tuple(group or None for group in match.groups())

    @classmethod
    def lookup(cls, basenote):
        """Look up note in registered annotations, walking class tree."""
        # Walk method resolution order, which includes current class.
        for c in cls.mro():
            if not hasattr(c, 'provider_registry'):
                # class is a mixin or super to this base class.
                continue
            if c not in c.provider_registry:
                # class registration functions never used.
                continue
            if basenote in c.provider_registry[c]:
                # note is in the registry.
                return c.provider_registry[c][basenote]
        raise LookupError(repr(basenote))

    # TODO: enter and exit as method and __method__

    # TODO: close -- call close all providers which have been called
    # keeping counts on all tokens resolved, not just bool, would be nice

    @classmethod
    def generator_to_provider(cls, note, fn):
        class LambdaProvider(Provider):
            provide = note
            def get(self, name=None):
                if hasattr(self, 'value'):
                    return self.value
                self.generator = fn()
                try:
                    self.value = six.next(self.generator)
                except StopIteration:
                    raise RuntimeError("generator didn't yield")
                return self.value
            def close(self):
                if not hasattr(self, 'generator'):
                    return
                try:
                    six.next(self.generator)
                except StopIteration:
                    return
                else:
                    raise RuntimeError("generator didn't stop")
        return LambdaProvider


# Annotations provide key data for jeni's injection.

def annotate(*notes, **keyword_notes):
    """Decorator-maker to annotate a given callable."""
    def decorator(fn):
        set_annotations(fn, *notes, **keyword_notes)
        return fn
    return decorator


def set_annotations(fn, *notes, **keyword_notes):
    """Set the annotations on the given callable."""
    if getattr(fn, '__annotations__', None):
        raise AttributeError('callable is already annotated: {!r}'.format(fn))
    check_for_extras(fn, keyword_notes)
    annotations = {}
    annotations.update(keyword_notes)
    args = get_function_arguments(fn)
    if len(notes) > len(args):
        msg = '{!r} takes {} arguments, but {} annotations given'
        raise TypeError(msg.format(fn, len(args), len(notes)))
    for arg_name, note in zip(args, notes):
        annotations[arg_name] = note
    if hasattr(fn, '__func__'):
        fn.__func__.__annotations__ = annotations
    else:
        fn.__annotations__ = annotations


def get_annotations(fn):
    """Get the annotations of a given callable."""
    annotations = getattr(fn, '__annotations__', None)
    if annotations:
        return annotations
    raise AttributeError('{!r} does not have annotations'.format(fn))


def has_annotations(fn):
    """True if callable is annotated, else False."""
    try:
        get_annotations(fn)
    except AttributeError:
        return False
    return True


def collect_notes(fn):
    """Format callable's annotations into notes, keyword_notes."""
    annotations = get_annotations(fn)
    args, keywords = get_named_positional_keyword_arguments(fn)
    notes = []
    keyword_notes = {}
    for arg in args:
        try:
            notes.append(annotations[arg])
        except KeyError:
            break
    for arg in keywords:
        try:
            keyword_notes[arg] = annotations[arg]
        except KeyError:
            continue
    return tuple(notes), keyword_notes


def check_for_extras(fn, keyword_notes):
    """Raise TypeError if function has too many keyword annotations."""
    if supports_extra_keywords(fn):
        return
    args = get_function_arguments(fn)
    for arg in keyword_notes:
        if arg not in args:
            msg = "{}() got an unexpected keyword annotation '{}'"
            raise TypeError(msg.format(fn.__name__, arg))


# Inspect utilities allow for manipulation of annotations.

def class_in_progress(stack=None):
    """True if currently inside a class definition, else False."""
    if stack is None:
        stack = inspect.stack()
    for frame in stack:
        statement_list = frame[4]
        if statement_list[0].strip().startswith('class '):
            return True
    return False


getargspec = getattr(inspect, 'getfullargspec', inspect.getargspec)


def get_function_arguments(fn):
    """Provide function argument names, skipping method's 'self'."""
    args = getargspec(fn).args
    if class_in_progress():
        args = args[1:]
    if hasattr(fn, '__self__'):
        args = args[1:]
    return args


def get_named_positional_keyword_arguments(fn):
    """Provide named (not *, **) positional, keyword arguments of callable."""
    argspec = getargspec(fn)
    args = get_function_arguments(fn)
    keywords = {}
    for default in reversed(argspec.defaults):
        keywords[args.pop()] = default
    return tuple(args), keywords


def supports_extra_keywords(fn):
    """True if callable catches unnamed keyword arguments, else False."""
    if hasattr(inspect, 'getfullargspec'):
        return inspect.getfullargspec(fn).varkw is not None
    return inspect.getargspec(fn).keywords is not None


if __name__ == '__main__':
    @Injector.generator('answer')
    def fn():
        print('before')
        yield 42
        print('after')

    injector = Injector()
    print(Injector.provider_registry)
    print(injector.fulfill('answer'))
    print(injector.resolve('answer'))

    Provider = Injector.generator_to_provider('answer', fn)
    provider = Provider()
    print(provider.get())
    print(provider.get())
    provider.close()

    Injector.factory(42, fn, generator=True)
    print(injector.resolve(42))

    class FooProvider(Provider):
        provide = 'foo'

        @annotate('bar', 'baz')
        def get(self, bar, baz, name=None):
            return bar, baz, 'foo'

    foo_provider = FooProvider()
    print(foo_provider.get('bar', 'baz'))
    print(collect_notes(foo_provider.get))
