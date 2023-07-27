#################################################
# Use Qiskit's QAOA implementation to solve for #
# the variables in an NchooseK environment      #
#################################################

# TODO Add session stuff! PULLLLLLLLLL

import datetime
import qiskit
import random
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

    def __repr__(self):
        ret = self._repr_dict()
        try:
            ret["Qiskit backend"] = self.sampler.backend
        except AttributeError:
            ret["Qiskit backend"] = 'unknown %s backend' % repr(self.sampler)
        ret["circuit depth"] = self.depth
        ret["total number of shots"] = self.total_shots
        ret["final number of shots"] = self.final_shots
        ret["number of jobs"] = self.num_jobs
        ret["samples"] = self.samples
        ret["job tags"] = self.job_tags
        return 'nchoosek.solver.Result(%s)' % str(ret)

    def __str__(self):
        ret = self._str_dict()
        ret["Qiskit backend"] = self._get_backend_name() or "[unknown]"
        ret["circuit depth"] = self.depth
        ret["total number of shots"] = self.total_shots
        ret["final number of shots"] = self.final_shots
        ret["number of jobs"] = self.num_jobs
        ret["number of unique samples"] = len(self.samples)
        ret["job tags"] = self.job_tags
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


def _construct_backendsampler(backend, tags):
    '''Construct a BackendSampler called sampler from the given backend
     parameter, which can be a Sampler, a Backend, a string, or None.'''
    # Create a sampler from the backend (which actually is allowed to
    # be a sampler).
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

    # Specify job tags unless the caller already specified them.
    if 'job_tags' not in sampler.options:
        sampler.set_options(job_tags=tags)
    return sampler


def solve(env, backend=None, hard_scale=None, optimizer=COBYLA(),
          reps=1, initial_point=None, callback=None):
    'Solve an NchooseK problem, returning a QiskitResult.'
    # Acquire a BackendSampler from the backend parameter and a list
    # of job tags.
    job_tags = ['NchooseK', 'nchoosek-%010x' % random.randrange(16**10)]
    sampler = _construct_backendsampler(backend, job_tags)

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
    # TODO Look here; try to find an easy way to evaluate 'energy' for each of
    # these things.
    # TODO I think that the function returned by the circuit_gen should work for
    # this, but the order could be all wrong for this version. Have to make a
    # different version?
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
    ret.num_samples = final_shots   # Number actually returned to the caller
    ret.num_jobs = num_jobs
    ret.tallies = [round(s.probability*ret.final_shots) for s in ret.samples]
    # TODO rearrange by 'energy' instead of tallies
    ret.tallies, ret.solutions = (list(x) for x in zip(*sorted(zip(ret.tallies, ret.solutions), key=lambda pair: pair[0])))
    ret.tallies.reverse()
    ret.solutions.reverse()
    try:
        ret.qubits = max([c.num_qubits for c in sampler.transpiled_circuits])
        ret.depth = max([c.depth() for c in sampler.transpiled_circuits])
    except AttributeError:
        ret.qubits = max([c.num_qubits for c in sampler.circuits])
        ret.depth = max([c.depth() for c in sampler.circuits])
    ret.job_tags = job_tags
    return ret
