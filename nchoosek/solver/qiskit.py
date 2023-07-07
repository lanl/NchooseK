#################################################
# Use Qiskit's QAOA implementation to solve for #
# the variables in an NchooseK environment      #
#################################################

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

try:
    import qiskit_ibm_runtime
except ModuleNotFoundError:
    pass


class QiskitResult(solver.Result):
    'Add Qiskit-specific fields to a Result.'

    def __repr__(self):
        ret = self._repr_dict()
        try:
            # BackendSampler has a backend attribute, but the other samplers
            # don't. Runtime Sampler has a session attribute which in turn has a
            # backend method, but it only gives a string.
            if isinstance(self.sampler, qiskit.primitives.BackendSampler):
                ret["Qiskit backend"] = self.sampler.backend.name
            else:
                ret["Qiskit backend"] = self.sampler.session.backend()
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
            if type(self.sampler) == qiskit.primitives.BackendSampler:
                backend = self.sampler.backend
            else:
                # This doesn't give us the backend itself, just the string.
                return self.sampler.session.backend()
        except AttributeError:
            # No backend
            return None
        if isinstance(backend.name, str):
            # BackendV2
            return backend.name
        else:
            # BackendV1
            return backend.configuration().backend_name

def _establish_runtime_backend(backend, service):
    '''For the sampler to be connected to the session, it needs to be
    created during the session. This returns a backend object and any
    included options.'''
    if isinstance(backend, BackendSampler):
        return service.backend(backend.backend.name), backend.options

    if isinstance(backend, qiskit_ibm_runtime.sampler.Sampler):
        # backend() returns the string name rather than the object itself
        # Cannot just return the sampler, as the sampler must be created
        # within the session.
        return service.backend(backend.session.backend()), backend.options

    if isinstance(backend, qiskit_ibm_runtime.ibm_backend.IBMBackend):
        return backend, None

    if isinstance(backend, Backend):
        # If it got this far, this is the wrong kind of backend.
        return service.backend(backend.name), None

    if isinstance(backend, str):
        return service.backend(backend), None

    else:
        # If none of the above were provided, abort.
        raise ValueError('failed to recognize %s'
                         ' as a Qiskit Backend or Sampler' %
                         repr(backend))

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
        try:
            if isinstance(backend, qiskit_ibm_runtime.ibm_backend.IBMBackend):
                # If a runtime Sampler is desired without generating a new
                # session, the Sampler itself must be passed in as backend. We
                # can't instantiate a runtime Sampler without a service object.
                ibm_provider = IBMProvider()
                ibm_backend = ibm_provider.get_backend(name=backend.name)
                sampler = BackendSampler(ibm_backend)
        except NameError:
            # qiskit_ibm_runtime isn't installed; continue on to abort
            pass
        # If none of the above were provided, abort.
        raise ValueError('failed to recognize %s'
                         ' as a Qiskit Backend or Sampler' %
                         repr(backend))

    # Specify job tags unless the caller already specified them.
    if 'job_tags' not in sampler.options:
        sampler.set_options(job_tags=tags)
    return sampler


def solve(env, backend=None, hard_scale=None, runtime_service=None,
          optimizer=COBYLA(), reps=1, initial_point=None, callback=None):
    'Solve an NchooseK problem, returning a QiskitResult.'
    # Acquire a Backend or BackendSampler from the backend parameter and a
    # list of job tags.
    if runtime_service:
        backend, options = _establish_runtime_backend(backend, runtime_service)
    else:
        sampler = _construct_backendsampler(backend, job_tags)

    job_tags = ['NchooseK', 'nchoosek-%010x' % random.randrange(16**10)]
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

    if runtime_service != None:
        # Run the problem with QAOA on IBM Runtime
        with qiskit_ibm_runtime.Session(service=runtime_service,
                                        backend=backend) as session:
            sampler = qiskit_ibm_runtime.Sampler(options=options)
            if 'job_tags' not in sampler.options:
                sampler.set_options(job_tags=job_tags)
            stime1 = datetime.datetime.now()
            qaoa = QAOA(sampler=sampler, optimizer=optimizer, reps=reps,
                        initial_point=initial_point, callback=callback_wrapper)
            alg = MinimumEigenOptimizer(qaoa)
            result = alg.solve(prog)
            stime2 = datetime.datetime.now()
            session.close()

    else:
        # Run the problem with QAOA on a BackendSampler
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
    ret.num_samples = final_shots   # Number actually returned to the caller
    ret.num_jobs = num_jobs
    ret.tallies = [round(s.probability*ret.final_shots) for s in ret.samples]
    try:
        ret.qubits = max([c.num_qubits for c in sampler.transpiled_circuits])
        ret.depth = max([c.depth() for c in sampler.transpiled_circuits])
    except AttributeError:
        # Runtime sampler doesn't store circuits for some reason
        if len(sampler.circuits) > 0:
            ret.qubits = max([c.num_qubits for c in sampler.circuits])
            ret.depth = max([c.depth() for c in sampler.circuits])
        else:
            ret.qubits = 0
            ret.depth = 0
    ret.job_tags = job_tags
    return ret
