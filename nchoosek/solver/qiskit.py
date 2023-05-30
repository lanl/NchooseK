#################################################
# Use Qiskit's QAOA implementation to solve for #
# the variables in an NchooseK environment      #
#################################################

import datetime
import qiskit
from qiskit import Aer
from qiskit.algorithms.minimum_eigensolvers import QAOA
from qiskit.algorithms.optimizers import COBYLA
from qiskit.primitives import BaseSampler, Sampler, BackendSampler
from qiskit.providers import Backend
from qiskit_ibm_provider import IBMProvider
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from nchoosek import solver
from nchoosek.solver import construct_qubo


class QiskitResult(solver.Result):
    'Add Qiskit-specific fields to a Result.'

    def __init__(self):
        super().__init__()
        self._jobIDs = None
        self._qubits = None
        self._depth = None
        self._computed_expensive = False

    def _compute_expensive_values(self):
        'Provide various values that require nontrivial time to compute.'
        try:
            device = self.sampler.backend
            jobs = device.jobs(limit=50,
                               start_datetime=self.solver_times[0],
                               end_datetime=self.solver_times[1])
            # Qiskit jobs don't tell you how many physical qubits were
            # used; we need to tally these ourselves.  jnum is a
            # representative job.  (The last job should be avoided.)  circ
            # is the first circuit of that representative job.
            jnum = len(jobs)//2   #
            circ = jobs[jnum].circuits()[0]
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
        try:
            ret["Qiskit backend"] = self.sampler.backend
        except AttributeError:
            ret["Qiskit backend"] = 'unknown %s backend' % repr(self.sampler)
        if self.jobIDs is not None:
            ret["number of jobs"] = len(self.jobIDs)
        if self.depth is not None:
            ret["circuit depth"] = self.depth
        if self.samples is not None:
            ret["samples"] = self.samples
        ret["total number of shots"] = self.total_shots
        ret["final number of shots"] = self.final_shots
        ret["number of jobs"] = self.num_jobs
        return 'nchoosek.solver.Result(%s)' % str(ret)

    def __str__(self):
        ret = self._str_dict()
        ret["Qiskit backend"] = self._get_backend_name() or "[unknown]"
        if self.jobIDs:
            ret["number of jobs"] = len(self.jobIDs)
        if self.depth:
            ret["circuit depth"] = self.depth
        ret["total number of shots"] = self.total_shots
        ret["final number of shots"] = self.final_shots
        ret["number of jobs"] = self.num_jobs
        if self.samples is not None:
            ret["number of unique samples"] = len(self.samples)
        return str(ret)

    def _get_backend_name(self):
        'Return the name of the backend or None if not available.'
        try:
            backend = self.sampler.backend
        except AttributeError:
            # No backend
            return None
        if isinstance(backend.name, str):
            # BackendV2
            return backend.name
        else:
            # BackendV1
            return backend.configuration().backend_name


def solve(env, backend=None, hard_scale=None, optimizer=COBYLA(),
          reps=1, initial_point=None, callback=None):
    'Solve an NchooseK problem, returning a QiskitResult.'
    # Construct a BackendSampler called sampler from the given backend
    # parameter, which can be a Sampler, a Backend, a string, or None.
    if isinstance(backend, BaseSampler):
        # If a Sampler was provided, use it.
        sampler = backend
    elif isinstance(backend, Backend):
        # If a Backend was provided, wrap it in a Sampler.
        sampler = BackendSampler(backend)
    elif isinstance(backend, str):
        # If a string was provided, use it as a backend name for the
        # default IBM provider.
        ibm_provider = IBMProvider()
        ibm_backend = ibm_provider.get_backend(name=backend)
        sampler = BackendSampler(ibm_backend)
    elif backend is None:
        # If nothing was provided, sample from a local simulator.
        sampler = BackendSampler(Aer.get_backend('aer_simulator'))
    else:
        # If none of the above were provided, abort.
        raise ValueError('failed to recognize %s'
                         ' as a Qiskit Backend or Sampler' %
                         repr(backend))

    # Convert the environment to a QUBO.
    qtime1 = datetime.datetime.now()
    qubo = construct_qubo(env, hard_scale)
    qtime2 = datetime.datetime.now()

    # Set up a QuadraticProgram for Qiskit.
    prog = QuadraticProgram('nck')
    for var in {e for qs in qubo for e in qs}:
        prog.binary_var(var)
    prog.minimize(quadratic=qubo)

    # Keep track of the number of shots and jobs.
    final_shots = 0   # Shots in final job; used for computing tallies
    total_shots = 0   # Total shots across all jobs
    num_jobs = 0      # Number of jobs submitted

    # Wrap the user's callback with one that records the final number
    # of shots.
    def callback_wrapper(n_evals, beta_gamma, energy, metadata):
        nonlocal final_shots, total_shots, num_jobs
        shots = metadata['shots']
        final_shots = shots
        total_shots += shots
        num_jobs += 1
        if callback is not None:
            callback(n_evals, beta_gamma, energy, metadata)

    # Run the problem with QAOA.
    stime1 = datetime.datetime.now()
    qaoa = QAOA(sampler=sampler, optimizer=optimizer, reps=reps,
                initial_point=initial_point, callback=callback_wrapper)
    alg = MinimumEigenOptimizer(qaoa)
    result = alg.solve(prog)

    stime2 = datetime.datetime.now()
    ret = QiskitResult()
    ret.variables = env.ports()
    ret.solutions = []
    vars = result.variables
    for samp in result.samples:
        ret.solutions.append({vars[i].name: x != 0
                              for i, x in enumerate(samp.x)
                              if vars[i].name in env.ports()})

    # Record this time now to ensure that the QAOA is done running first.
    ret.qubo_times = (qtime1, qtime2)
    ret.solver_times = (stime1, stime2)
    ret.sampler = sampler
    ret.samples = result.samples
    ret.final_shots = final_shots
    ret.total_shots = total_shots
    ret.num_jobs = num_jobs
    ret.tallies = [round(s.probability*ret.final_shots) for s in ret.samples]
    return ret
