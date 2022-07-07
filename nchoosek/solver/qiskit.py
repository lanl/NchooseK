#################################################
# Use Qiskit's QAOA implementation to solve for #
# the variables in an NchooseK environment      #
#################################################

import datetime
import qiskit
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit.algorithms import QAOA
from qiskit.algorithms.optimizers import COBYLA
from qiskit.utils import QuantumInstance
from nchoosek import solver
from nchoosek.solver import construct_qubo


class QiskitResult(solver.Result):
    'Add Qiskit-specific fields to a Result.'

    def __init__(self):
        super().__init__()
        self.quantum_instance = None

    def __repr__(self):
        ret = self._repr_dict()
        ret["Qiskit backend"] = self.quantum_instance.backend
        return 'nchoosek.solver.Result(%s)' % str(ret)

    def __str__(self):
        ret = self._str_dict()
        ret["Qiskit backend"] = self.quantum_instance.backend.name()
        return str(ret)


def solve(env, quantum_instance=None, hard_scale=None, optimizer=COBYLA()):
    # If there is no quantum_instance given, run it on a simulator on the
    # computer running the program.
    if not quantum_instance:
        backend = qiskit.Aer.get_backend('qasm_simulator')
        quantum_instance = QuantumInstance(backend)

    # Convert the environment to a QUBO.
    qubo = construct_qubo(env, hard_scale)

    # Set up a QuadraticProgram for Qiskit.
    prog = QuadraticProgram('nck')
    for var in {e for qs in qubo for e in qs}:
        prog.binary_var(var)
    prog.minimize(quadratic=qubo)

    time1 = datetime.datetime.now()
    # This runs the problem as a QAOA.
    qaoa = MinimumEigenOptimizer(QAOA(optimizer=optimizer, reps=1,
                                 quantum_instance=quantum_instance))
    result = qaoa.solve(prog)
    ret = QiskitResult()
    ret.variables = env.ports()
    ret.solutions = []
    ret.solutions.append({k: v != 0
                          for k, v in result.variables_dict.items()
                          if k in env.ports()})
    # Record this time now to ensure that the QAOA is done running first.
    time2 = datetime.datetime.now()
    ret.times = (time1, time2)
    ret.tallies = [1]
    ret.quantum_instance = quantum_instance
    return ret
