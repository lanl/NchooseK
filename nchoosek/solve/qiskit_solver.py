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
from qiskit.utils import QuantumInstance


class ConstraintConversionError(Exception):
    'A constraint could not be converted to a QUBO.'

    def __init__(self, c):
        msg = 'failed to convert constraint to a QUBO: %s' % str(c)
        super().__init__(msg)

def solve(env, quantum_instance=None, hard_scale=10, optimizer=COBYLA()):
    
    # If there is no quantum_instance given, run it on a simulator on the
    # computer running the program.
    if not quantum_instance:
        quantum_instance = QuantumInstance(qiskit.Aer.get_backend('qasm_simulator'))
        
    prog = QuadraticProgram('nck')
    # This dictionary will be passed to the Quadratic Program.
    quad_dict = defaultdict(lambda: 0)
    # This adds the non-ancillary qubits to the Quadratic Program.
    for port in env.ports():
        prog.binary_var(port)
    # This will create a set to keep track of ancillary variables.
    var_set = set()
    # This counter will keep track of how many ancilla bits there are in the
    # problem
    i = 0

    for constr in env.constraints():
        # This counter keeps track of how many ancilla bits there are in the
        # qubo
        cnt = 0
        qubo, _ = constr.solve_qubo()
        if qubo == None:
            raise ConstraintConversionError(str(c))
        for q1, q2, val in qubo:
            # These two conditionals are needed to name the ancilla bits
            # properly. Each qubo will start with _anc1, and the Program needs
            # differently named ones.
            if q1[:4] == "_anc":
                idx = int(q1[4:])
                q1 = "_anc" + str(idx + i)
                # Each ancillary qubit will show up in the first position at
                # least once. It will only occur more than once if there are
                # more than one ancillary qubit, but because the Quadratic
                # Program will fail if it receives more than one occurance of a
                # single variable, it needs to check whether it's already in
                # the Program first.
                if q1 not in var_set:
                    var_set.add(q1)
                    prog.binary_var(q1)
                if idx > cnt:
                    cnt = idx
            if q2[:4] == "_anc":
                idx = int(q2[4:])
                q2 = "_anc" + str(idx + i)
            # If the constraint is soft it needs to have less impact than if
            # it's hard.
            if not constr.soft:
                val *= hard_scale
            quad_dict[(q1, q2)] += val
        i += cnt
        # Large programs could have a lot of ancillary qubits. Enough to be
        # worth going through the overhead of emptying the set every time?
        # var_set.empty()
    # This will set up the quadratic program for Qiskit.
    prog.minimize(quadratic=quad_dict)
    
    # This runs the problem as a QAOA
    qaoa = MinimumEigenOptimizer(QAOA(optimizer=optimizer, reps=1,
                                 quantum_instance=quantum_instance))
    result = qaoa.solve(prog)

    # Need to return both the answer and the results, to give the job IDs.
    return result.variables_dict
