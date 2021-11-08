# Load the core NchooseK functionality.
from nchoosek.core import *

# Load a solver based on the setting of the NCHOOSEK_SOLVER
# environment variable
import os
import sys
_solver_name = os.getenv('NCHOOSEK_SOLVER')
if _solver_name is None or _solver_name == 'z3':
    import nchoosek.solver.z3
    solve = nchoosek.solver.z3.solve
elif _solver_name == 'ocean':
    import nchoosek.solver.ocean
    solve = nchoosek.solver.ocean.solve
elif _solver_name == 'qiskit':
    import nchoosek.solver.qiskit
    solve = nchoosek.solver.qiskit.solve
else:
    raise ValueError('"%s" (from NCHOOSEK_SOLVER) is not a recognized '
                     'NchooseK solver' % _solver_name)
