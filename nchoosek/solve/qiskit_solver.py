########################################
# Use qiskit QAOA to solve for the     #
# variables in an NchooseK environment #
########################################

from collections import defaultdict
import qiskit
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit.algorithms import QAOA
from qiskit.algorithms.optimizers import COBYLA


class ConstraintConversionError(Exception):
    'A constraint could not be converted to a QUBO.'

    def __init__(self, c):
        msg = 'failed to convert constraint to a QUBO: %s' % str(c)
        super().__init__(msg)

def solve(env, quantum_instance, hard_scale=10, optimizer=COBYLA()):
    # optimizer.set_options(maxiter=500)
    
    prog = QuadraticProgram('nck')
    quad_dict = defaultdict(lambda: 0)
    for port in env.ports():
        prog.binary_var(port)
    for constr in env.constraints():
        qubo, _ = constr.solve_qubo()
        if qubo == None:
            print("This is an error holdover")
        for q1, q2, val in qubo:
            if not constr.soft:
                val *= hard_scale
            quad_dict[(q1, q2)] += val
    prog.minimize(quadratic=quad_dict)
    
    qaoa = MinimumEigenOptimizer(QAOA(optimizer=optimizer, reps=1, quantum_instance=quantum_instance))
    result = qaoa.solve(prog)
    return result.variables_dict
