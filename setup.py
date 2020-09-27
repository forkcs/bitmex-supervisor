from setuptools import setup

import supervisor

install_requires = [req[:-1] for req in open('requirements.txt').readlines()]

setup(
    name='bitmex-supervisor',
    description='Automated monitoring of orders/positions on your BitMEX account.',
    version=supervisor.__version__,
    packages=['supervisor', 'supervisor.core', 'supervisor.core.auth',
              'supervisor.core.utils'],
    install_requires=install_requires,
    url='https://github.com/forkcs/bitmex-supervisor'
)
