# Load the core NchooseK functionality.
from nchoosek.core import *
import os


def _name_to_solver(name):
    '''Map a solver name to an appropriate solve function.  Raise a ValueError
    if the name is not recognized.'''
    if name == 'z3':
        import nchoosek.solver.z3
        return nchoosek.solver.z3.solve
    elif name == 'ocean':
        import nchoosek.solver.ocean
        return nchoosek.solver.ocean.solve
    elif name == 'qiskit':
        import nchoosek.solver.qiskit
        return nchoosek.solver.qiskit.solve
    else:
        raise ValueError('"%s" is not a recognized NchooseK solver' % name)


# Load a solver based on the setting of the NCHOOSEK_SOLVER environment
# variable.
_solver_name = os.getenv('NCHOOSEK_SOLVER')
if _solver_name is None:
    _solver_name = 'z3'
solve = _name_to_solver(_solver_name)


def solver_name():
    'Return the name of the solver being used.'
    return _solver_name
