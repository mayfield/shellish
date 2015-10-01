#!/usr/bin/env python

from setuptools import setup, find_packages

README = 'README.md'

def long_desc():
    try:
        import pypandoc
    except ImportError:
        with open(README) as f:
            return f.read()
    else:
        return pypandoc.convert(README, 'rst')

setup(
    name='shellish',
    version='0.7.0',
    description='A framework for CLI/shell programs.',
    author='Justin Mayfield',
    author_email='tooker@gmail.com',
    url='https://github.com/mayfield/shellish/',
    license='MIT',
    long_description=long_desc(),
    packages=find_packages(),
    install_requires=[],
    test_suite='test',
    entry_points = {
        'console_scripts': ['csvpretty=shellish.tools.csvpretty:csvpretty']
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        #'Development Status :: 4 - Beta',
        #'Development Status :: 5 - Production/Stable',
        #'Development Status :: 6 - Mature',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries',
        'Topic :: System :: Shells',
    ]
)
