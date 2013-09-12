====================================
 jeni: dependency aggregation (dip)
====================================

**jeni** lets you build applications and not e.g. web applications.

Overview
========

1. Define a set of dependencies that your system uses.
2. Give your code natural call interfaces accepting those dependencies.
3. Implement a **Provider** which can fulfill those dependencies in one call.

This is **dependency aggregation**. Gather your dependencies into namespaces,
use those namespaces to annotate callables, then implement those namespaces for
the various contexts in which your application will need to run.

jeni runs on Python 2.7, Python 3.2, Python 3.3, and pypy.


Motivation
==========

Write code as its meant to be written, without pegging your call signatures to
some monolithic object that only applies to a specific runtime. This is about
more than just testing. This lets you write composable utilities.

jeni's design principle is to have all annotated callables usable in a context
that knows nothing about jeni. Any callable is as relevant to a fresh Python
REPL as it is to a Provider.


Annotations
===========

Annotations are implemented as decorators and not Python3 annotations in order
to support Python2 and to allow for callables to have multiple annotations.


API
===

``BaseProvider``
----------------

Abstract base class to aggregate dependencies into a namespace.

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


``BaseProvider.annotate(cls, *notes, **keyword_notes)``
-------------------------------------------------------

Build a decorator to annotate dependencies of a callable.

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
requested dependency is valid but null and ``UNSET`` when the provider
is unable to provide the requested dependency. An ``UNSET`` return
value triggers an error condition on positional arguments, but in the
case of keyword arguments, an ``UNSET`` value will result in that
keyword argument not being passed to the annotated callable.


``BaseProvider.apply(self, fn)``
--------------------------------

Fully apply annotated callable, returning callable's result.


``BaseProvider.partial(self, fn)``
----------------------------------

Partially apply annotated callable, returning a partial function.


``BaseProvider.implement(cls, *provider_classes)``
--------------------------------------------------

Implement annotations of other providers without subclassing.


``BaseProvider.extend(self, *providers)``
-----------------------------------------

Extend providers, using their accessors when not provided by self.

Providers in the extension list are accessed in the order in which they
are registered, and are only used for methods and NOT attributes.
Accessing a non-method/non-function attribute will only attempt to
access that attribute on ``self``. Note that properties/descriptors
test as methods and not the type of their return value.

This approach allows a provider to expose another provider's methods
without collisions with private attributes and memoization patterns
where the current provider uses the same names as the extended
provider.


License
=======

Copyright (c) 2013 Ron DuPlain <ron.duplain@gmail.com> (see AUTHORS file).

Released under the BSD License (see LICENSE file).
