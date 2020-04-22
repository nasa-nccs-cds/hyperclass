#!/usr/bin/env python

from setuptools import setup, find_packages
with open("README.md", "r") as fh:
    long_description = fh.read()

install_requires = set()
with open( "requirements/hyperclass.txt" ) as f:
  for dep in f.read().split('\n'):
      if dep.strip() != '' and not dep.startswith('-e'):
          install_requires.add( dep )

setup(name='geoproc',
      version='0.0.1',
      description='Methods for hyperspectral image classification',
      author='Thomas Maxwell',
      zip_safe=False,
      author_email='thomas.maxwell@nasa.gov',
      url='https://github.com/nasa-nccs-cds/hyperclass.git',
      long_description=long_description,
      long_description_content_type="text/markdown",
      packages=find_packages(),
      install_requires=list(install_requires),
      classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)

