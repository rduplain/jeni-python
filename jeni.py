# jeni.py
# Copyright 2013-2014 Ron DuPlain <ron.duplain@gmail.com> (see AUTHORS file).
# Released under the BSD License (see LICENSE file).

"""jeni: dependency injection through annotations (dip)."""

__version__ = '0.3-dev'

import abc
import functools
import inspect
import re
import sys

import six


class UnsetError(LookupError):
    """Note is not able to be provided, as it is currently unset."""
    def __init__(self, *a, **kw):
        self.note = kw.pop('note', None)
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
    re_note = re.compile(r'^(.*?)(?::(.*))?$') # annotation is 'object:name'

    def __init__(self):
        self.instances = {}

    @classmethod
    def provider(cls, *provider_seq):
        for provider in provider_seq:
            cls.register(provider.provide, provider)
        if len(provider_seq) == 1:
            # Support use as a decorator.
            return provider_seq[0]

    @classmethod
    def factory(cls, note, fn=None):
        def decorator(f):
            if inspect.isgeneratorfunction(f):
                provider = cls.generator_to_provider(note, f)
                cls.register(note, provider)
            else:
                cls.register(note, f)
            return f
        if fn is None:
            return decorator
        return decorator(fn)

    def apply(self, fn):
        args, kwargs = self.prepare(fn)
        return fn(*args, **kwargs)

    def partial(self, fn):
        args, kwargs = self.prepare(fn)
        return functools.partial(fn, *args, **kwargs)

    def prepare(self, fn):
        notes, keyword_notes = collect_notes(fn)
        args, kwargs = self.fulfill(*notes, **keyword_notes)
        return args, kwargs

    def fulfill(self, *notes, **keyword_notes):
        """Fulfill injection during function application."""
        args = tuple(self.resolve(note) for note in notes)
        kwargs = {}
        for arg in keyword_notes:
            # TODO: Maybe.
            note = keyword_notes[arg]
            try:
                kwargs[arg] = self.resolve(note)
            except UnsetError:
                continue
        return args, kwargs

    def resolve(self, note):
        """Resolve a single note into an object."""
        basenote, name = self.parse_note(note)
        try:
            provider_or_fn = self.lookup(basenote)
        except LookupError:
            msg = "Unable to resolve '{}'"
            raise LookupError(msg.format(note))
        return self.handle_provider(provider_or_fn, note, basenote, name=name)

    def handle_provider(self, provider_or_fn, note, basenote, name=None):
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
        try:
            if name is not None:
                return fn(name=name)
            return fn()
        except UnsetError:
            # Use sys.exc_info to support both Python 2 and Python 3.
            exc_type, exc_value, tb = sys.exc_info()
            exc_value.note = note
            six.reraise(exc_type, exc_value, tb)

    @classmethod
    def parse_note(cls, note):
        """Parse string annotation into object reference with optional name."""
        if isinstance(note, tuple):
            if len(note) != 2:
                raise ValueError('tuple annotations must be length 2')
            return note
        try:
            match = cls.re_note.match(note)
        except TypeError:
            # Note is not a string. Support any Python object as a note.
            return note, None
        return match.groups()

    @classmethod
    def register(cls, note, provider):
        basenote, name = cls.parse_note(note)
        if 'provider_registry' not in cls.__dict__:
            cls.provider_registry = {}
        cls.__dict__['provider_registry'][basenote] = provider

    @classmethod
    def lookup(cls, basenote):
        """Look up note in registered annotations, walking class tree."""
        # Walk method resolution order, which includes current class.
        for c in cls.mro():
            if 'provider_registry' not in c.__dict__:
                # class is a mixin, super to base class, or never registered.
                continue
            if basenote in c.provider_registry:
                # note is in the registry.
                return c.provider_registry[basenote]
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
        if statement_list is None:
            continue
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
    for default in reversed(argspec.defaults or []):
        keywords[args.pop()] = default
    return tuple(args), keywords


def supports_extra_keywords(fn):
    """True if callable catches unnamed keyword arguments, else False."""
    if hasattr(inspect, 'getfullargspec'):
        return inspect.getfullargspec(fn).varkw is not None
    return inspect.getargspec(fn).keywords is not None


if __name__ == '__main__':
    @Injector.factory('answer')
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

    Injector.factory(42, fn)
    print(injector.resolve(42))

    @Injector.provider
    class FooProvider(Provider):
        provide = 'foo'

        @annotate('bar', 'baz')
        def get(self, bar, baz, name=None):
            return bar, baz, 'foo'

    foo_provider = FooProvider()
    print(foo_provider.get('bar', 'baz'))
    print(collect_notes(foo_provider.get))

    @Injector.factory('error')
    def error():
        raise UnsetError

    @annotate('error')
    def positional_error(error):
        print('You should not see me.')

    @annotate('answer', unused='error')
    def keyword_error(answer, unused=None):
        assert unused is None

    try:
        injector.apply(positional_error)
    except UnsetError:
        err = sys.exc_info()[1]
        assert err.note == 'error'

    injector.apply(keyword_error)

    class SubInjector(Injector):
        pass

    SubInjector.factory('universe', fn)
    sub_injector = SubInjector()
    print(sub_injector.fulfill('answer'))
