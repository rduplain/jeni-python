#!/usr/bin/env python
"""An unsafe, naive .rst processor to support minimal module documentation."""

from __future__ import print_function

import inspect
import os
import re
import sys


directive_re = re.compile(r'\.\. (eval|exec)::(.*)') # only supports one-liners


doc = """``{name}``
{underline}

{doc}
"""

def insert_doc(obj, u='-', name=None):
    if name is None:
        name = obj.__name__
    return doc.format(
        name=name,
        underline=u*(len(name)+4),
        doc=inspect.getdoc(obj) or '')


args_doc = """``{name}{argspec}``
{underline}

{doc}
"""

def insert_args_doc(obj, u='-', ns=None, name=None):
    spec = inspect.getargspec(obj)
    if name is None:
        name = obj.__name__
    if ns is not None:
        name = '{}.{}'.format(ns, name)
    argspec = inspect.formatargspec(*spec)
    return args_doc.format(
        name=name,
        underline=u*(len(name+argspec)+4),
        argspec=argspec,
        doc=inspect.getdoc(obj) or '')


def process(filename, warning=os.environ.get('RST_WARNING', None)):
    context = dict(
        insert_doc=insert_doc,
        insert_args_doc=insert_args_doc)
    if warning:
        yield '.. {}\n\n'.format(warning)
    for line in open(filename):
        match = directive_re.search(line)
        if match is not None:
            expression = '{}\n'.format(match.group(2).strip())
            if match.group(1) == 'exec':
                result = None
                exec(expression, {}, context)
            else:
                result = eval(expression, {}, context)
            if result:
                yield result
            continue
        yield line


def main(argv, fd=sys.stdout):
    if len(argv) < 2:
        print('no input file', file=sys.stderr)
        return 2
    for filename in argv[1:]:
        for line in process(filename):
            fd.write(line)
            fd.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
