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
        'celery>=4.1.1<5',
        'dataclasses',

        # 'apistar==0.4.3',
        'coreapi>=2.3.3<3',
        'jinja2>=2.10<3',
        'pytest>=3.6.0<4',
        'requests>=2.18.4<3',
        'werkzeug>=0.14.1<1',
        'whitenoise>=3.3.1<4'
    ],
    tests_require=[
        'pytest'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: System :: Networking',
        'Programming Language :: Python :: 3.6',
    ],
)
