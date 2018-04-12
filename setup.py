#!/usr/bin/env python

from setuptools import setup


setup(
    name='celerystar',
    version='0.0.1',
    url='http://gerenciagram.com.br',
    license='MIT',
    description='Celery based task framework with dependency injection',
    author=['Pedro Lacerda', 'Tassio Guimarães'],
    author_email='pslacerda+dev@gmail.com',
    py_modules=['celerystar'],
    install_requires=[
        'apistar',
        'celery>=4.2.0rc2',
        'dataclasses',
    ],
    tests_require=[
        'pytest'
    ],
    dependency_links=[
        "git://github.com/encode/apistar.git@level-up#egg=apistar"
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: Linux',
        'Topic :: System :: Networking',
         'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
    ],
)
