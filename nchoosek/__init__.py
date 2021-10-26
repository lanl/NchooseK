# Load the core NchooseK functionality.
from nchoosek.core import *

# Load a solver based on the setting of the NCHOOSEK_SOLVER
# environment variable
import os
import sys
_solver_name = os.getenv('NCHOOSEK_SOLVER')
if _solver_name == None or _solver_name == 'z3':
    from nchoosek.solver import z3
    solve = z3.solve
elif _solver_name == 'ocean':
    from nchoosek.solver import ocean
    solve = ocean.solve
else:
    raise RuntimeError('"%s" (from NCHOOSEK_SOLVER) is not a recognized NchooseK solver' % _solver_name)
