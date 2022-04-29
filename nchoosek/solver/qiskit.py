#################################################
# Use Qiskit's QAOA implementation to solve for #
# the variables in an NchooseK environment      #
#################################################

from nchoosek import solver
from nchoosek.solver import construct_qubo
import qiskit
import datetime
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
    ret = solver.Result()

    ret.solutions = []
    ret.solutions.append({k: v != 0 for k, v in result.variables_dict.items() if k in env.ports()})
    # Record this time now to ensure that the QAOA is done running first.
    time2 = datetime.datetime.now()
    ret.times = (time1, time2)
    ret.tallies = [1]
    ret.quantum_instance = quantum_instance

    # Convert the result to a mapping from port names to Booleans and
    # return it.
    ports = env.ports()
    return ret
