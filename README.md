NchooseK
========

NchooseK is an experiment in providing portable programming across classical computers, quantum annealers, and circuit-model quantum computers.  Its initial implementation is as an embedded domain-specific language—a Python module that provides a set of basic programming primitives, which the programmer combines using ordinary Python code.

Key concept
-----------

NchooseK is based on a single primitive, `nck`, which establishes a constraint, "*k* of these *n* Boolean values must be True".  For example, `nck([A, B, C], {1})` dictates that exactly one of variables *A*, *B*, and *C* must be True and the rest must be False.  *k* can be a set containing multiple values: `nck([A, B, C], {0, 3})` dictates that either all three of *A*, *B*, and *C* are False or all three are True.

Variables can appear multiple times in the first argument.  All instances of a variable will receive the same True/False value.  As an example, `nck([A, B, B], {2})` has a single solution: *A* = False and *B* = True.  Any other assignment of True and False would result in 0, 1, or 3 of [*A*, *B*, *B*] being True.

A program can—and typically does—specify multiple `nck` constraints.  `nck([A, B, C], {1}); nck([B, C, D], {1}); nck([C, D, E], {1})` dictates that exactly one of {*A*, *B*, *C*}, exactly one of [*B*, *C*, *D*], and exactly one of [*C*, *D*, *E*] must be True.  Hence, one possible solution sets *A* and *E* True and the rest of the variables False; another possible solution sets only *C* True and the rest False.

Constraints can be either "hard" (the default) or "soft".  Hard constraints must be satisfied for a solution to be valid.  Soft constraints will be satisfied if possible but can be violated if necessary.  Indicate a soft constraint by appending a `soft=True` argument to an `nck` constraint.

That's it!  NchooseK may seem simplistic, but our hypothesis is that it is sufficiently general as to express a wide variety of computational problems yet sufficiently simple as to facilitate implementation across highly disparate computational platforms.

Documentation
-------------

Documentation is forthcoming.  For the time being, please refer to the examples in the [examples](examples) subdirectory.  The main idea is to instantiate an `nchoosek.Environment`, which is basically a name space.  The environment's `register_port` method defines a variable, and the environment's `nck` method establishes a constraint given a list of ports and a set of allowable numbers of True ports.

Different solvers eventually will be supported.  Currently, only three exist: `z3`, which uses Microsoft Research's classical [Z3 Theorem Prover](https://github.com/Z3Prover/z3), `ocean`, which uses D-Wave's [Ocean](https://ocean.dwavesys.com/) to run either classically or on a quantum computer, and `qiskit`, which uses IBM's [Qiskit](https://www.qiskit.org/) to run either classically or on a quantum computer.  Specify one of those in your `NCHOOSEK_SOLVER` environment variable or as the optional `solver` argument to the environment's `solve` method (default: `z3`).  Invoke the `solve` method on the environment to solve for the value of every variable in the environment.  `solve` accepts solver-specific parameters, which also can be provided via the `NCHOOSEK_PARAMS` environment variable.

As a convenience, the environment's `new_type` method defines a reusable constraint that can be applied to different sets of inputs.

Installation
------------

```Python
python setup.py install
```

Legal statement
---------------

Copyright © 2021 Triad National Security, LLC.
All rights reserved.

This program was produced under U.S. Government contract 89233218CNA000001 for Los Alamos National Laboratory (LANL), which is operated by Triad National Security, LLC for the U.S.  Department of Energy/National Nuclear Security Administration. All rights in the program are reserved by Triad National Security, LLC, and the U.S. Department of Energy/National Nuclear Security Administration. The Government is granted for itself and others acting on its behalf a nonexclusive, paid-up, irrevocable worldwide license in this material to reproduce, prepare derivative works, distribute copies to the public, perform publicly and display publicly, and to permit others to do so.

This program is open source under the [BSD-3 License](LICENSE.md).  Its LANL-internal identifier is C21038.

Contact
-------

Scott Pakin, *pakin@lanl.gov*
