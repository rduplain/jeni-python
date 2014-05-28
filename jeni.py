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


# TODO: Update all docstrings, rewrite README.

class UnsetError(LookupError):
    """Note is not able to be provided, as it is currently unset."""
    def __init__(self, *a, **kw):
        self.note = kw.pop('note', None)
        super(UnsetError, self).__init__(*a, **kw)


# Motivation: dependency injection using prepared providers.

@six.add_metaclass(abc.ABCMeta)
class Provider(object):
    @abc.abstractmethod
    def get(self, name=None):
        "Implement in sub-class."

    def close(self):
        "By default, does nothing."


class GeneratorProvider(Provider):
    def __init__(self, function, support_name=False):
        self.function = function
        self.support_name = support_name
        self.initialized = False

    def init(self, *a, **kw):
        self.generator = self.function(*a, **kw)
        try:
            self.init_value = next(self.generator)
        except StopIteration:
            msg = "generator didn't yield: function {!r}"
            raise RuntimeError(msg.format(self.function))
        else:
            self.initialized = True
            return self.init_value

    def get(self, name=None):
        if not self.initialized:
            msg = '{!r} not initialized; call `init` before `get`.'
            raise RuntimeError(msg.format(self))
        if name is None:
            return self.init_value
        elif not self.support_name:
            msg = "generator does not support get-by-name: function {!r}"
            raise TypeError(msg.format(self.function))
        try:
            value = self.generator.send(name)
        except StopIteration:
            msg = "generator didn't yield: function {!r}"
            raise RuntimeError(msg.format(self.function))
        return value

    def close(self):
        if not self.initialized:
            raise RuntimeError('{!r} not initialized'.format(self))
        if self.support_name:
            self.generator.close()
        try:
            next(self.generator)
        except StopIteration:
            return
        else:
            msg = "generator didn't stop: function {!r}"
            raise RuntimeError(msg.format(self.function))


class Annotator(object):
    """Annotate callables. Intended to be stateless dict of function pointers.

    Annotations on callables are data for jeni's injection.
    Built as a class to embed annotation helpers and support customization.
    """

    # TODO: Support base-case to opt-in a function annotated in Python 3.
    # TODO: Support annotation to inject partial.

    def __call__(self, *notes, **keyword_notes):
        """Decorator-maker to annotate a given callable."""
        def decorator(fn):
            self.set_annotations(fn, *notes, **keyword_notes)
            return fn
        return decorator

    def get_annotations(self, fn):
        """Get the annotations of a given callable."""
        __notes__ = getattr(fn, '__notes__', None)
        if __notes__:
            return __notes__
        raise AttributeError('{!r} does not have annotations'.format(fn))

    def set_annotations(self, fn, *notes, **keyword_notes):
        """Set the annotations on the given callable."""
        if getattr(fn, '__notes__', None):
            raise AttributeError('callable already has notes: {!r}'.format(fn))
        fn.__notes__ = (notes, keyword_notes)

    def has_annotations(self, fn):
        """True if callable is annotated, else False."""
        try:
            self.get_annotations(fn)
        except AttributeError:
            return False
        return True

annotate = Annotator()


class Injector(object):
    """Collects dependencies and reads annotations to fulfill them."""
    annotator_class = Annotator
    generator_provider = GeneratorProvider
    re_note = re.compile(r'^(.*?)(?::(.*))?$') # annotation is 'object:name'

    def __init__(self):
        annotator = self.annotator_class()
        self.get_annotations = annotator.get_annotations
        self.set_annotations = annotator.set_annotations
        self.has_annotations = annotator.has_annotations

        self.closed = False
        self.instances = {}
        self.values = {}

    @classmethod
    def provider(cls, note, provider=None, name=False):
        def decorator(fn_or_class):
            if inspect.isgeneratorfunction(fn_or_class):
                fn = fn_or_class
                fn.support_name = name
                cls.register(note, fn)
            else:
                provider = fn_or_class
                if not hasattr(provider, 'get'):
                    msg = "{!r} does not meet provider interface with 'get'"
                    raise ValueError(msg.format(provider))
                cls.register(note, provider)
            return fn_or_class
        if provider is not None:
            decorator(provider)
        else:
            return decorator

    @classmethod
    def factory(cls, note, fn=None):
        if fn is not None:
            cls.register(note, fn)
        else:
            def decorator(f):
                cls.register(note, f)
                return f
            return decorator

    def apply(self, fn):
        args, kwargs = self.prepare(fn)
        return fn(*args, **kwargs)

    def partial(self, fn):
        args, kwargs = self.prepare(fn)
        return functools.partial(fn, *args, **kwargs)

    def close(self):
        # TODO: have an opinion about order of closed
        # TODO: keeping counts on tokens resolved, not just bool, would be nice
        if self.closed:
            raise RuntimeError('{!r} already closed'.format(self))
        for provider in self.instances.values():
            provider.close()
        self.closed = True

    def prepare(self, fn):
        notes, keyword_notes = self.get_annotations(fn)
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
        if name is None and basenote in self.values:
            return self.values[basenote]
        try:
            provider_or_fn = self.lookup(basenote)
        except LookupError:
            msg = "Unable to resolve '{}'"
            raise LookupError(msg.format(note))
        return self.handle_provider(provider_or_fn, note, basenote, name=name)

    def handle_provider(self, provider_or_fn, note, basenote, name=None):
        if basenote in self.instances:
            provider_or_fn = self.instances[basenote]
        elif inspect.isclass(provider_or_fn):
            provider_or_fn = provider_or_fn()
            self.instances[basenote] = provider_or_fn
        elif inspect.isgeneratorfunction(provider_or_fn):
            provider_or_fn, value = self.init_generator(provider_or_fn)
            self.instances[basenote] = provider_or_fn
            self.values[basenote] = value
            if name is None:
                return value
        if hasattr(provider_or_fn, 'get'):
            fn = provider_or_fn.get
        else:
            fn = provider_or_fn
        if self.has_annotations(fn):
            fn = self.partial(fn)
        try:
            if name is None:
                value = fn()
                self.values[basenote] = value
                return value
            return fn(name=name)
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
        if 'provider_registry' not in vars(cls):
            cls.provider_registry = {}
        cls.provider_registry[basenote] = provider

    @classmethod
    def lookup(cls, basenote):
        """Look up note in registered annotations, walking class tree."""
        # Walk method resolution order, which includes current class.
        for c in cls.mro():
            if 'provider_registry' not in vars(c):
                # class is a mixin, super to base class, or never registered.
                continue
            if basenote in c.provider_registry:
                # note is in the registry.
                return c.provider_registry[basenote]
        raise LookupError(repr(basenote))

    def init_generator(self, fn):
        provider = self.generator_provider(fn, support_name=fn.support_name)
        if self.has_annotations(provider.function):
            notes, keyword_notes = self.get_annotations(provider.function)
            args, kwargs = self.fulfill(*notes, **keyword_notes)
            value = provider.init(*args, **kwargs)
        else:
            value = provider.init()
        return provider, value

    # TODO: enter and exit as method and __method__



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
