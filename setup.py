####################
# Install NchooseK #
####################

import setuptools

long_description = ('NchooseK is a constraint-programming system that is very '
                    'limited in features but designed for portability across '
                    'novel hardware platforms, in particular quantum '
                    'annealers and circuit-model quantum computers.')

setuptools.setup(
    name='nchoosek',
    version='1.0.0',
    description='The NchooseK constraint-programming system',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Scott Pakin',
    author_email='pakin@lanl.gov',
    classifiers=[
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers'],
    keywords=[
        'linear programming',
        'constraint programming',
        'optimization'
        'quantum computing',
        'quantum annealing'],
    url='https://github.com/lanl/NchooseK',
    license='LICENSE.md',
    python_requires='>=3.8',
    install_requires=[
        'z3-solver >= 4.8',
    ],
    packages=setuptools.find_packages(),
    scripts=['bin/tt2nck'])
