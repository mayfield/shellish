#!/usr/bin/env python
from setuptools import setup, find_packages


def long_desc():
    with open('README.md') as f:
        return f.read()


setup(
    name='shellish',
    version='5.1',
    description='A framework for CLI/shell programs.',
    author='Justin Mayfield',
    author_email='tooker@gmail.com',
    url='https://github.com/mayfield/shellish/',
    license='MIT',
    long_description=long_desc(),
    long_description_content_type='text/markdown',
    packages=find_packages(),
    install_requires=['markdown2'],
    test_suite='test',
    entry_points={
        'console_scripts': [
            'csvpretty=shellish.tools.csvpretty:csvpretty',
            'mdcat=shellish.tools.mdcat:mdcat'
        ]
    },
    classifiers=[
        'Development Status :: 6 - Mature',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.11',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Shells',
    ]
)
