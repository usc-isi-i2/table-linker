from distutils.core import setup
from setuptools import find_packages
from tl import __version__

with open('requirements.txt', 'r') as f:
    install_requires = list()
    dependency_links = list()
    for line in f:
        re = line.strip()
        if re:
            if re.startswith('git+') or re.startswith('svn+') or re.startswith('hg+'):
                dependency_links.append(re)
            else:
                install_requires.append(re)

packages = find_packages()

setup(
    name='table-linker',
    version=__version__,
    packages=packages,
    url='https://github.com/usc-isi-i2/table-linker',
    license='MIT',
    author='Amandeep Singh',
    include_package_data=True,
    install_requires=install_requires,
    dependency_links=dependency_links,
    entry_points={
        'console_scripts': [
            'tl = tl.cli_entry:cli_entry',
        ],
    },
)