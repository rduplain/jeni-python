# jeni.py
# Copyright (c) 2013 Ron DuPlain <ron.duplain@gmail.com> (see AUTHORS file).
# Released under the BSD License (see LICENSE file).

"""jeni: dependency aggregation (dip)."""

__version__ = '0.2-dev'

import functools
import re
import types


# Sentinel object that indicates a dependency cannot be fulfilled.
UNSET = object()


class UnsetError(KeyError):
    """Note could possibly be provided, but is currently unset."""


class BaseProvider(object):
    """Abstract base class to aggregate dependencies into a namespace.

    The primary operations of a Provider are to **annotate** a callable and to
    **apply** that callable (partially or fully) by passing in the dependencies
    declared in the annotation.

    This allows application dependencies to be aggregated in one place, to be
    declared using a namespaced annotation (possibly annotating multiple times
    with different namespaces), and to have multiple interface-compatible
    implementations of those dependencies through subclasses of the Provider
    which annotated the callable.

    A Provider can optionally expose the dependencies of other providers
    through the **extend** operation or implement the annotations of other
    providers through the **implement** operation.
    """

    class_annotation = {} # registry: {class: {callable: (notes, keywords)}}
    class_implements = {} # registry: {class: classes}
    accessor_pattern = 'get_{}' # naming convention of dependency accessors
    re_close_method = re.compile(r'^close_.*') # dependency close methods
    re_note = re.compile(r'([^:]*):?(.*)') # annotation format: 'object:name'
    before_close = [] # optional order of method names to call first on `close`

    @classmethod
    def annotate(cls, *notes, **keyword_notes):
        """Build a decorator to annotate dependencies of a callable.

        The annotation informs the provider class how to apply the callable::

            @Provider.annotate('dependency1', 'dependency2:name_therein')
            def some_callable(dependency1, named_object_from_dependency2):
                "Just a callable doing its thing."

        An instance of the provider class can then apply the callable::

            provider.apply(some_callable)
            fn = provider.partial(some_callable); fn()

        Annotations support keywords to allow callables to specify default
        values. The name of the keyword note should match the name of the
        keyword argument::

            @Provider.annotate('dependency1', foo='dependency3')
            def some_other_callable(dependency1, foo=default_value):
                "Just a callable with a default doing its thing."

        Callables can use additional positional arguments or keyword arguments
        by use of the Provider's partial operation, where the caller can get a
        partial function which has resolved the annotated dependencies and
        requires additional arguments.

        Annotations are registered on the base provider class, namespaced by
        the class whose method performed the annotation, and do not alter the
        annotated callable in any way. Argument notes in the annotation are
        used for simple lookups on the instance, where:

        1. A note in the form of 'dependency1' calls the ``get_dependency1``
           instance method.

        2. A note in the form of 'dependency2:name_therein' calls the
           ``get_dependency2`` instance method, passing ``name='name_therein'``
           as a keyword argument which the method can use to lookup a specific
           object that it provides.

        The method's return value in either form is entirely up to the
        implementation. The ``get_dependency`` accessor pattern is a convention
        which is configurable using the ``accessor_pattern`` class attribute or
        ``format_accessor_name`` method.

        Provider implementations of accessors should return ``None`` when the
        requested dependency is valid but null and ``UNSET`` when the Provider
        is unable to provide the requested dependency. An ``UNSET`` return
        value triggers an error condition on positional arguments, but in the
        case of keyword arguments, an ``UNSET`` value will result in that
        keyword argument not being passed to the annotated callable.
        """
        if cls not in cls.class_annotation:
            cls.class_annotation[cls] = {}
        def decorator(fn):
            """Register callable with Provider without modifying callable."""
            cls.class_annotation[cls][fn] = (notes, keyword_notes)
            return fn
        return decorator

    @classmethod
    def unannotate(cls, fn):
        """Remove callable annotation from class, inverse of ``annotate``."""
        cls.class_annotation[cls].pop(fn)

    def apply(self, fn):
        """Fully apply annotated callable, returning callable's result."""
        notes, keyword_notes = self.lookup(fn)
        args, kwargs = self.resolve_notes(*notes, **keyword_notes)
        return fn(*args, **kwargs)

    def partial(self, fn):
        """Partially apply annotated callable, returning a partial function."""
        notes, keyword_notes = self.lookup(fn)
        args, kwargs = self.resolve_notes(*notes, **keyword_notes)
        return functools.partial(fn, *args, **kwargs)

    def close(self):
        """Close Provider resources, for use in cleanup and not critical path.

        A Provider's **close** operation will call all ``close_dependency``
        methods of the provider instance, even if the corresponding accessor
        was never called. Therefore, these close methods should function
        correctly even if the ``get_dependency`` accessor was never called. The
        ``close_dependency`` method pattern is a convention which is
        configurable by customizing the ``is_close_method`` method. Methods
        called during ``close`` do not take any arguments.

        Methods listed (by strings matching the method name) in the
        ``before_close`` class attribute (list) are called in order before
        scanning for ``close_dependency`` methods on the Provider. Each method
        called is called only once during ``close``.

        A Provider's close operation will only call close methods that the
        Provider defines, even if it is extending another Provider
        instance. This is to ensure that each Provider instance has its own
        lifecycle with explicit calls to the close operation.

        Provider close methods should not intentionally raise errors.
        Specifically, if a dependency has transactions, the transaction should
        be committed or rolled back before close is called, and not left as an
        operation to be called during the close phase.
        """
        called = set()
        for name in self.before_close:
            if name in called:
                continue
            method = getattr(self, name)
            method()
            called.add(name)
        for name in dir(self):
            if name in called:
                continue
            if not self.is_close_method(name):
                continue
            method = getattr(self, name)
            method()
            called.add(name)

    @classmethod
    def implement(cls, *provider_classes):
        """Implement annotations of other Providers without subclassing."""
        if cls not in cls.class_implements:
            cls.class_implements[cls] = []
        cls.class_implements[cls].extend(provider_classes)

    @classmethod
    def lookup(cls, fn):
        """Look up callable in registered annotations, walking class tree."""
        for other_class in cls.mro():
            if not hasattr(other_class, 'class_annotation'):
                # other_class is a mixin or super to this base class.
                continue
            if other_class not in other_class.class_annotation:
                # other_class.annotate never used.
                continue
            if fn in other_class.class_annotation[other_class]:
                # Function instance is in the registry.
                return other_class.class_annotation[other_class][fn]
            if hasattr(fn, '__func__') and \
               fn.__func__ in other_class.class_annotation[other_class]:
                # Method's function instance is in the registry.
                return other_class.class_annotation[other_class][fn.__func__]
        for other_class in cls.class_implements.get(cls, []):
            try:
                return other_class.lookup(fn)
            except LookupError:
                continue
        raise LookupError(repr(fn))

    def resolve_notes(self, *notes, **keyword_notes):
        """Resolve full annotation into objects during function application."""
        args = tuple(self.resolve_note(note) for note in notes)
        kwargs = {k: self.resolve_note(v) for k, v in keyword_notes.items()}
        for arg, note in zip(args, notes):
            if arg is UNSET:
                msg = "'{}' is unable to provide '{}'.".format(self, note)
                raise UnsetError(msg)
        kwargs = {k: v for k, v in kwargs.items() if v is not UNSET}
        return args, kwargs

    def resolve_note(self, note):
        """Resolve a single note into an object."""
        object_name, name = self.parse_note(note)
        accessor_name = self.format_accessor_name(object_name)
        accessor = getattr(self, accessor_name)
        if name:
            return accessor(name=name)
        return accessor()

    def parse_note(self, note):
        """Parse string annotation into object reference with optional name."""
        match = self.re_note.match(note)
        return tuple(group or None for group in match.groups())

    def format_accessor_name(self, object_name):
        """Given object name, return accessor name which provides object."""
        return self.accessor_pattern.format(object_name)

    def is_close_method(self, name):
        """Indicate whether method name is for a dependency close method."""
        return self.re_close_method.search(name) is not None

    def extend(self, *providers):
        """Extend Providers, using their accessors when not provided by self.

        Providers in the extension list are accessed in the order in which they
        are registered, and are only used for methods and NOT attributes.
        Accessing a non-method/non-function attribute will only attempt to
        access that attribute on ``self``. Note that properties/descriptors
        test as methods and not the type of their return value.

        This approach allows a Provider to expose another Provider's methods
        without collisions with private attributes and memoization patterns
        where the current Provider uses the same names as the extended
        Provider.
        """
        extends = getattr(self, 'extends', [])
        extends.extend(providers) # Python heard that you like to extend.
        self.extends = extends

    def unextend(self, *providers):
        """Remove provider extension, inverse of ``extend``."""
        extends = getattr(self, 'extends', [])
        for provider in providers:
            extends.remove(provider)
        self.extends = extends

    def __getattr__(self, name):
        """Get attribute, falling back to extension Providers' methods."""
        if name == 'extends':
            # Avoid infinite recursion.
            return object.__getattribute__(self, name)
        try:
            # First try self.
            return object.__getattribute__(self, name)
        except AttributeError:
            pass
        # Then try each provider in extends list, accepting methods/functions.
        for provider in getattr(self, 'extends', []):
            try:
                attr = getattr(provider, name)
                if isinstance(attr, (types.MethodType, types.FunctionType)):
                    return attr
            except AttributeError:
                continue
        # Finally, fail.
        return object.__getattribute__(self, name) # AttributeError

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
