from setuptools import setup
import re
import os

with open('{}/README.md'.format(os.path.split(os.path.abspath(__file__))[0]), 'r') as inf:
    long_description = inf.read()

with open('{}/src/r2g/__init__.py'.format(os.path.split(os.path.abspath(__file__))[0]), 'r') as inf:
    version = re.findall(r'__version__ = "(.+)"', inf.read())[0]

setup(
    name='r2g',
    version=version,
    license="MIT",
    url='https://github.com/yangwu91/r2g.git',
    author='Yang Wu',
    author_email='wuyang@drwu.ga',
    maintainer="Yang Wu",
    maintainer_email="wuyang@drwu.ga",
    description='A computationally lightweight and homology-based pipeline that allows rapid identification of '
                'genes or gene families from raw sequence databases in the absence of an assembly',
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires='>=3.6',
    scripts=['src/scripts/r2g'],
    py_modules=['r2g.errors', ],
    packages=[
        "r2g",
        "r2g.utils",
        "r2g.local",
        "r2g.online"
    ],
    package_dir={"": "src"},
    package_data={'r2g': ['*.json', ]},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        # Technically the license is not OSI approved,
        # but almost there, so might put:
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Scientific/Engineering :: Bio-Informatics"
    ],
    install_requires=["requests~=2.24.0", "selenium~=3.141.0"],
    extras_require={
        'test': ["pytest", "pytest-cov", "codecov"],
    },
)
