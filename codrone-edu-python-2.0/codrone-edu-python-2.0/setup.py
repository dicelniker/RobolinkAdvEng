from setuptools import setup, find_packages

setup_requires = [
    ]

install_requires = [
    'pyserial>=3.5',
    'numpy',
    'colorama',
    'Pillow',
    'scikit-learn'
    ]

dependency_links = [
    ]
desc = """\
Python package for controlling CoDrone EDU. 
"""

setup(
    name='codrone_edu',
    version='2.0',
    description='Python CoDrone EDU library',
    url='',
    author='Robolink',
    author_email='info@robolink.com',
    keywords=['codrone', 'edu'],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    setup_requires=setup_requires,
    dependency_links=dependency_links,
    python_requires='>=3.5',
    )
