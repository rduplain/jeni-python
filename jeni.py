import abc
import inspect

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
    # register(provider...) -- classmethod
    # register function -- return value, no close
    # register generator -- yield value, then continuation to close

    # partial

    # apply

    # following work with self and delegate to parent:

    # fulfill - resolve notes into dependencies

    # enter and exit as method and __method__

    # close -- call close all providers which have been called
    # keeping counts on all tokens resolved, not just bool, would be nice

    pass


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
    class FooProvider(Provider):
        provide = 'foo'

        @annotate('bar', 'baz')
        def get(self, bar, baz, name=None):
            return bar, baz, 'foo'

    foo_provider = FooProvider()
    print(foo_provider.get('bar', 'baz'))
    print(collect_notes(foo_provider.get))
