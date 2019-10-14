#!/usr/bin/env python

from setuptools import setup
from pathlib import Path
import pygment


readme_path = Path(__file__).absolute().parent / "README.md"

with readme_path.open() as f:
    long_desc = f.read()


setup(name='pygmend',
      version=pygment.__version__,
      description='Format google style docstrings',
      long_description=long_desc,
      long_description_content_type="text/markdown",
      author='Sambhav Kothari',
      author_email='sambhavs.email@gmail.com',
      license='GPLv3',
      keywords="pygment docstring googledoc development generate auto",
      platforms=['any'],
      classifiers=[
          'Intended Audience :: Developers',
          'Topic :: Documentation',
          'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7'
          ],
      url='https://github.com/samj1912/pygmend',
      packages=['pygment'],
      python_requires='>=3.6',
      entry_points={
        'console_scripts': [
            'pygmend = pygmend:main'
            ]
        },
      )
