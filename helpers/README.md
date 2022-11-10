Helper programs
===============

This directory is intended to hold programs that a user of NchooseK may find useful.

tt2nck
------

This program converts a truth table to an NchooseK constraint.  Compile it from its Haskell source code with
```bash
ghc -O2 tt2nck.hs
```

**tt2nck** inputs a truth table, which is provided via a filename on the command line or read from standard input if no filename is provided.  It outputs the number of times each variable needs to be repeated, the selection set, and an example of a complete NchooseK constraint that uses *A*, *B*, *C*, etc. as variable names.

For example, given the truth table for a Boolean OR function,
```
0 0 0
0 1 1
1 0 1
1 1 1
```
**tt2nck** will output the following:
```
Repetitions: [1,1,2] (4 total)
Tallies:     [0,3,4]
Example:     nck([A,B,C,C], [0,3,4])
```

The program employs an exhaustive search so it can take an extremely long time to process truth tables containing a large number of columns.

Programmer documentation for **tt2nck** can be generated using Haddock:
```bash
haddock --html tt2nck.hs
```

qubo-cache.sqlite3
------------------

NchooseK uses a [QUBO](https://en.wikipedia.org/wiki/Quadratic_unconstrained_binary_optimization) (quadratic unconstrained binary optimization problem) as its intermediate representation.  Each NchooseK constraint is converted to a QUBO, then these are summed and submitted to the quantum computer.  Unfortunately, constraints containing large variable collections and selection sets can take an extremely long time to convert to QUBOs.  To speed up compilation, NchooseK caches prior conversions of constraints to QUBOs.  If the `NCHOOSEK_QUBO_CACHE` environment variable names a
[SQLite](https://www.sqlite.org/) database file, these conversions will persist across runs.

For speed of compilation and user convenience, NchooseK provides a pre-populated QUBO-cache database, `qubo-cache.sqlite3`.  This database maps *all* NchooseK constraints on 1 to 8 variables to a QUBO.  The database contains 17,122 entries:
```console
$ sqlite3 qubo-cache.sqlite3 'select count(*) from qubo_cache;'
17122
```

It is highly recommended that all users point `NCHOOSEK_QUBO_CACHE` to `qubo-cache.sqlite3` to eliminate potentially high run-time costs of QUBO generation.

`qubo-cache.sqlite3` was created using **populate-qubo-cache** and **merge-qubo-caches**, described below.

populate-qubo-cache
-------------------

**populate-qubo-cache** generates an exhaustive set of constraints and invokes NchooseK to convert each to a QUBO, storing the result in the qubo-cache database.  (Be sure to set `NCHOOSEK_QUBO_CACHE` before running the program, or the results will not be saved!)  For example, **populate-qubo-cache** considers the following constraints for variable collections of size 1, 2, and 3:

```Python
nck(['X0'], {0})
nck(['X0'], {1})
nck(['X0'], {0, 1})
nck(['X0', 'X1'], {0})
nck(['X1', 'X1'], {0})
nck(['X0', 'X1'], {1})
nck(['X1', 'X1'], {1})
nck(['X0', 'X1'], {0, 1})
nck(['X1', 'X1'], {0, 1})
nck(['X0', 'X1'], {2})
nck(['X1', 'X1'], {2})
nck(['X0', 'X1'], {0, 2})
nck(['X1', 'X1'], {0, 2})
nck(['X0', 'X1'], {1, 2})
nck(['X1', 'X1'], {1, 2})
nck(['X0', 'X1'], {0, 1, 2})
nck(['X1', 'X1'], {0, 1, 2})
nck(['X0', 'X1', 'X2'], {0})
nck(['X1', 'X2', 'X2'], {0})
nck(['X2', 'X2', 'X2'], {0})
nck(['X0', 'X1', 'X2'], {1})
nck(['X1', 'X2', 'X2'], {1})
nck(['X2', 'X2', 'X2'], {1})
nck(['X0', 'X1', 'X2'], {0, 1})
nck(['X1', 'X2', 'X2'], {0, 1})
nck(['X2', 'X2', 'X2'], {0, 1})
nck(['X0', 'X1', 'X2'], {2})
nck(['X1', 'X2', 'X2'], {2})
nck(['X2', 'X2', 'X2'], {2})
nck(['X0', 'X1', 'X2'], {0, 2})
nck(['X1', 'X2', 'X2'], {0, 2})
nck(['X2', 'X2', 'X2'], {0, 2})
nck(['X0', 'X1', 'X2'], {1, 2})
nck(['X1', 'X2', 'X2'], {1, 2})
nck(['X2', 'X2', 'X2'], {1, 2})
nck(['X0', 'X1', 'X2'], {0, 1, 2})
nck(['X1', 'X2', 'X2'], {0, 1, 2})
nck(['X2', 'X2', 'X2'], {0, 1, 2})
nck(['X0', 'X1', 'X2'], {3})
nck(['X1', 'X2', 'X2'], {3})
nck(['X2', 'X2', 'X2'], {3})
nck(['X0', 'X1', 'X2'], {0, 3})
nck(['X1', 'X2', 'X2'], {0, 3})
nck(['X2', 'X2', 'X2'], {0, 3})
nck(['X0', 'X1', 'X2'], {1, 3})
nck(['X1', 'X2', 'X2'], {1, 3})
nck(['X2', 'X2', 'X2'], {1, 3})
nck(['X0', 'X1', 'X2'], {0, 1, 3})
nck(['X1', 'X2', 'X2'], {0, 1, 3})
nck(['X2', 'X2', 'X2'], {0, 1, 3})
nck(['X0', 'X1', 'X2'], {2, 3})
nck(['X1', 'X2', 'X2'], {2, 3})
nck(['X2', 'X2', 'X2'], {2, 3})
nck(['X0', 'X1', 'X2'], {0, 2, 3})
nck(['X1', 'X2', 'X2'], {0, 2, 3})
nck(['X2', 'X2', 'X2'], {0, 2, 3})
nck(['X0', 'X1', 'X2'], {1, 2, 3})
nck(['X1', 'X2', 'X2'], {1, 2, 3})
nck(['X2', 'X2', 'X2'], {1, 2, 3})
nck(['X0', 'X1', 'X2'], {0, 1, 2, 3})
nck(['X1', 'X2', 'X2'], {0, 1, 2, 3})
nck(['X2', 'X2', 'X2'], {0, 1, 2, 3})
```

All other constraints on 1–3 variables are isomorphic to one of the above.

Common command-line options are `--min-vars` and `--max-vars`, which specify respectively the minimum and maximum number of variables (including repetition) to consider per constraint.  The `--parallel` option controls the number of worker processes to spawn to accelerate execution.  It defaults to the number of CPUs.

Less common command-line options include `--initial-skip` and `--step`.  These are used when distributing **populate-qubo-cache** across multiple computers.  `--initial-skip` defaults to 0, and `--step` defaults to 1.  `--initial-skip` indicates the number of constraints in the ordered list of constraints not to convert to QUBOs.  `--step` indicates the increment of the index into the constraint list for constraints to convert to QUBOs.  For instance, each of the following five commands could be run on a separate computer to divide up the work five ways:
```bash
populate-qubo-cache --initial-skip=0 --step=5
populate-qubo-cache --initial-skip=1 --step=5
populate-qubo-cache --initial-skip=2 --step=5
populate-qubo-cache --initial-skip=3 --step=5
populate-qubo-cache --initial-skip=4 --step=5
```

It is recommended to specify a different `NCHOOSEK_QUBO_CACHE` environment variable for each instance of **populate-qubo-cache**.  This not only improves performance by reducing contention for a single database file but also reduces the likelihood of the program aborting due to an inability to acquire the database lock within a timeout period.  The separate databases later can be merged with **merge-qubo-caches**, described below.

merge-qubo-caches
-----------------

**merge-qubo-caches** merges multiple QUBO-cache databases into a single database.  It takes as input the target database file, which will be created if it does not exist, followed by a list of source database files whose contents will be copied to the target.
