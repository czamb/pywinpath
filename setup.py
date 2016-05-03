import os
import io
import sys
from setuptools import setup

with io.open('pywinpath.py', 'r', encoding='utf-8') as source:
    version_ln = [ln for ln in source if ln.startswith('__version__')][0]
    version = version_ln.replace('__version__ = ', '').replace('\'', '')

with io.open('README.rst', 'r', encoding='utf-8') as readme_file:
    readme = readme_file.read()

long_description = readme

# requirements = [colorama]

#setup(
setup_params = dict(
    name='pywinpath',
    version=version,
    description=('A command-line utility for MS Windows '
                 'to keep the Windows PATH variable tidy and short.'),
    long_description=long_description,
    author='czam.de',
    author_email='pywinpath@ca.czam.de',
    url='https://github.com/czamb/PyWinPath',
    py_modules=['pywinpath'],
    entry_points={
        'console_scripts': [
            'pywinpath = pywinpath:main',
        ]
    },
    include_package_data=True,
    #install_requires=requirements,
    extras_require = {'color': ["colorama"]},
    license='BSD',
    #zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Win32 (MS Windows)',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: Microsoft :: Windows :: Windows 7',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Utilities',
    ],
    keywords=('PATH, Windows, cmd.exe, console, system search path, registry'),
)

if __name__ == '__main__':
    setup(**setup_params)
