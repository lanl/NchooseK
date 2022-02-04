#################################################
# Use Qiskit's QAOA implementation to solve for #
# the variables in an NchooseK environment      #
#################################################

from collections import defaultdict
from nchoosek.solver import ConstraintConversionError
import qiskit
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit.algorithms import QAOA
from qiskit.algorithms.optimizers import COBYLA
from qiskit.utils import QuantumInstance


def solve(env, quantum_instance=None, hard_scale=None, optimizer=COBYLA()):
    # If there is no quantum_instance given, run it on a simulator on the
    # computer running the program.
    if not quantum_instance:
        backend = qiskit.Aer.get_backend('qasm_simulator')
        quantum_instance = QuantumInstance(backend)

    # Scale the weight of hard constraints by either a user-specified value or
    # by an amount greater than the total weight of all soft constraints.
    if hard_scale is None:
        # A hard constraint is worth 1 more than all soft constraints combined.
        hard_scale = 1
        for c in env.constraints():
            if c.soft:
                hard_scale += 1

    prog = QuadraticProgram('nck')
    # This dictionary will be passed to the QuadraticProgram.
    quad_dict = defaultdict(lambda: 0)
    # This adds the non-ancillary qubits to the QuadraticProgram.
    for port in env.ports():
        prog.binary_var(port)
    # This will create a set to keep track of ancillary variables.
    var_set = set()
    # This counter will keep track of how many ancilla bits there are in the
    # problem.
    i = 0

    for constr in env.constraints():
        # This counter keeps track of how many ancilla bits there are in the
        # QUBO.
        cnt = 0
        qubo, _ = constr.solve_qubo()
        if qubo is None:
            raise ConstraintConversionError(str(c))
        for q1, q2, val in qubo:
            # These two conditionals are needed to name the ancilla bits
            # properly. Each QUBO will start with _anc1, and the Program needs
            # differently named ones.
            if q1[:4] == "_anc":
                idx = int(q1[4:])
                q1 = "_anc" + str(idx + i)
                # Each ancillary qubit will show up in the first position at
                # least once. It will only occur more than once if there are
                # more than one ancillary qubit, but because the
                # QuadraticProgram will fail if it receives more than one
                # occurance of a single variable, it needs to check whether
                # it's already in the Program first.
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
    # This will set up the QuadraticProgram for Qiskit.
    prog.minimize(quadratic=quad_dict)

    # This runs the problem as a QAOA.
    qaoa = MinimumEigenOptimizer(QAOA(optimizer=optimizer, reps=1,
                                 quantum_instance=quantum_instance))
    result = qaoa.solve(prog)

    # Need to return both the answer and the results, to give the job IDs.
    return result.variables_dict
