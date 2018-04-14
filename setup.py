#!/usr/bin/env python

from setuptools import setup, find_packages


setup(
    name='celerystar',
    version='0.0.1',
    url='http://gerenciagram.com.br',
    license='MIT',
    description='Celery based task framework with dependency injection',
    author=['Pedro Lacerda', 'Tassio Guimarães'],
    author_email='pslacerda+dev@gmail.com',
    packages=find_packages(),
    package_data={
        'celerystar': ['static/*']
    },
    install_requires=[
        'celery>=4.2.0rc2',
        'dataclasses',

        # 'apistar==0.4.3',
        'coreapi',
        'jinja2',
        'pytest',
        'requests',
        'werkzeug',
        'whitenoise'
    ],
    tests_require=[
        'pytest'
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
