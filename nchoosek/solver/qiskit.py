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
        self._jobIDs = None
        self._qubits = None
        self._depth = None
        self._computed_expensive = False

    def _compute_expensive_values(self):
        'Provide various values that require nontrivial time to compute.'
        try:
            device = self.quantum_instance.backend
            jobs = device.jobs(limit=50,
                               start_datetime=self.solver_times[0],
                               end_datetime=self.solver_times[1])
            # Qiskit jobs don't tell you how many physical qubits get used;
            # we need to tally these ourself.
            jnum = len(jobs)//2   # Representative job (last should be avoided)
            circ = jobs[jnum].circuits()[0]  # 1st circuit of a representative job
            self._qubits = len({q
                                for d in circ.data
                                if d[0].name != 'barrier'
                                for q in d[1]})
            self._jobIDs = []
            for job in jobs:
                self._jobIDs.append(job.job_id())
            self._depth = circ.depth()
        except AttributeError:
            # Qiskit's local simulator lacks a jobs field.
            pass
        self._computed_expensive = True

    @property
    def qubits(self):
        'Return the number of physical qubits used.'
        if not self._computed_expensive:
            self._compute_expensive_values()
        return self._qubits

    @qubits.setter
    def qubits(self, value):
        # This function exists so the base class can write "qubits = None".
        pass

    @property
    def jobIDs(self):
        'Return a list of job IDs.'
        if not self._computed_expensive:
            self._compute_expensive_values()
        return self._jobIDs

    @property
    def depth(self):
        'Return the circuit depth.'
        if not self._computed_expensive:
            self._compute_expensive_values()
        return self._depth

    def __repr__(self):
        ret = self._repr_dict()
        ret["Qiskit backend"] = self.quantum_instance.backend
        if self.jobIDs:
            ret["number of jobs"] = len(self.jobIDs)
        if self.depth:
            ret["circuit depth"] = self.depth
        return 'nchoosek.solver.Result(%s)' % str(ret)

    def __str__(self):
        ret = self._str_dict()
        ret["Qiskit backend"] = self.quantum_instance.backend.name()
        if self.jobIDs:
            ret["number of jobs"] = len(self.jobIDs)
        if self.depth:
            ret["circuit depth"] = self.depth
        return str(ret)

def _construct_quantum_instance(desc):
    'Construct a QuantumInstance from a a string description.'
    if qiskit.IBMQ.active_account() is None:
        qiskit.IBMQ.load_account()
    fields = desc.split('/')
    hub, group, project, system = None, None, None, None
    nf = len(fields)
    if nf >= 1 and fields[-1] != '*':
        system = fields[-1]
    if nf >= 2 and fields[-2] != '*':
        project = fields[-2]
    if nf >= 3 and fields[-3] != '*':
        group = fields[-3]
    if nf >= 4 and fields[-4] != '*':
        hub = fields[-4]
    if nf >= 5:
        raise ValueError('QuantumInstance must be of the form hub/group/project/system')
    providers = qiskit.IBMQ.providers(hub=hub, group=group, project=project)
    backend = None
    for provider in providers:
        if system is None:
            backend = qiskit.providers.ibmq.least_busy(provider.backends())
            break
        backends = provider.backends(name=system)
        if len(backends) > 0:
            backend = backends[0]
            break
    if backend is None:
        raise RuntimeError('Failed to find a quantum backend described by "%s"' % desc)
    return QuantumInstance(backend)

def solve(env, quantum_instance=None, hard_scale=None, optimizer=COBYLA(),
          reps=1, initial_point=None, callback=None):
    'Solve an NchooseK problem, returning a QiskitResult.'
    # If no quantum_instance was given, run the circuit on a local
    # simulator.  If a quantum_instances was provided as a string,
    # construct a QuantumInstance based on that string's specification.
    if not quantum_instance:
        backend = qiskit.Aer.get_backend('qasm_simulator')
        quantum_instance = QuantumInstance(backend)
    elif isinstance(quantum_instance, str):
        quantum_instance = _construct_quantum_instance(quantum_instance)

    # Convert the environment to a QUBO.
    qtime1 = datetime.datetime.now()
    qubo = construct_qubo(env, hard_scale)
    qtime2 = datetime.datetime.now()

    # Set up a QuadraticProgram for Qiskit.
    prog = QuadraticProgram('nck')
    for var in {e for qs in qubo for e in qs}:
        prog.binary_var(var)
    prog.minimize(quadratic=qubo)

    # Run the problem with QAOA.
    stime1 = datetime.datetime.now()
    qaoa = MinimumEigenOptimizer(QAOA(optimizer=optimizer, reps=reps,
                                 initial_point=initial_point,
                                 callback=callback,
                                 quantum_instance=quantum_instance))
    result = qaoa.solve(prog)
    stime2 = datetime.datetime.now()
    ret = QiskitResult()
    ret.variables = env.ports()
    ret.solutions = []
    ret.solutions.append({k: v != 0
                          for k, v in result.variables_dict.items()
                          if k in env.ports()})
    # Record this time now to ensure that the QAOA is done running first.
    ret.qubo_times = (qtime1, qtime2)
    ret.solver_times = (stime1, stime2)
    ret.tallies = [1]
    ret.quantum_instance = quantum_instance
    return ret
