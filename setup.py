from distutils.core import setup

from jeni import __version__


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
    'Programming Language :: Python :: Implementation :: PyPy',
    'Topic :: Utilities',
    'Topic :: Software Development :: Libraries :: Python Modules']


setup(
    name='jeni',
    version=__version__,
    url='https://github.com/rduplain/jeni-python',
    license='BSD',
    author='Ron DuPlain',
    author_email='ron.duplain@gmail.com',
    description='dependency aggregation',
    py_modules=['jeni'],
    requires=[],
    classifiers=CLASSIFIERS)