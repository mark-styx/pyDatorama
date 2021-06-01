from setuptools import find_packages,setup

setup(
    name='pyDatorama',
    packages=find_packages(),
    version='0.10',
    description="A Python API wrapping library for Salesforce's datorama platform.",
    author='Mark Styx',
    install_requires=['pandas']
)