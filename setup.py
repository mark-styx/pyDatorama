from setuptools import find_packages,setup

setup(
    name='DatoramaFD',
    packages=find_packages(),
    version='0.1.39',
    description='Tool to interface with the Datorama API (platform only at this point).',
    author='Mark Styx',
    install_requires=['wheel','numpy','pandas','requests','datetime']
)