from os import path

from setuptools import setup


CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.2',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: Implementation :: PyPy',
    'Topic :: Utilities',
    'Topic :: Software Development :: Libraries :: Python Modules']


def extract_version(filepath='jeni.py', name='__version__'):
    """Parse __version__ out of given Python file.

    Given jeni.py has dependencies, `from jeni import __version__` will fail.
    """
    context = {}
    for line in open(filepath):
        if name in line:
            exec(line, context)
            break
    else:
        raise RuntimeError('{} not found in {}'.format(name, filepath))
    return context[name]


README = 'README.txt'
if not path.exists(README):
    README = 'README.rst'

with open(path.join(path.dirname(__file__), README)) as fd:
    long_description = '\n' + fd.read()


setup(
    name='jeni',
    version=extract_version(),
    url='https://github.com/rduplain/jeni-python',
    license='BSD',
    author='Ron DuPlain',
    author_email='ron.duplain@gmail.com',
    description='jeni injects annotated dependencies',
    long_description=long_description,
    py_modules=['jeni'],
    install_requires=[
        'six',
    ],
    classifiers=CLASSIFIERS)
