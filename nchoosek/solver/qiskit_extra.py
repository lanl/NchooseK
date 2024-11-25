import datetime
import random

import numpy as np
import qiskit
import qiskit_aer as Aer
import scipy.optimize

# from qiskit.algorithms.optimizers import COBYLA
from qiskit.primitives import BackendSampler, BaseSampler
from qiskit.providers import Backend, Provider

from nchoosek import solver


class QiskitResult(solver.Result):
    "Add Qiskit-specific fields to a Result."

    def __repr__(self):
        ret = self._repr_dict()
        try:
            ret["Qiskit backend"] = self.sampler.backend
        except AttributeError:
            ret["Qiskit backend"] = "unknown %s backend" % repr(self.sampler)
        ret["circuit depth"] = self.depth
        ret["total number of shots"] = self.total_shots
        ret["final number of shots"] = self.final_shots
        ret["number of jobs"] = self.num_jobs
        # ret["samples"] = self.samples
        ret["job tags"] = self.job_tags
        ret["tallies"] = self.tallies
        return "nchoosek.solver.Result(%s)" % str(ret)

    def __str__(self):
        ret = self._str_dict()
        ret["Qiskit backend"] = self._get_backend_name() or "[unknown]"
        ret["circuit depth"] = self.depth
        ret["total number of shots"] = self.total_shots
        ret["final number of shots"] = self.final_shots
        ret["number of jobs"] = self.num_jobs
        # ret["number of unique samples"] = len(self.samples)
        ret["job tags"] = self.job_tags
        return str(ret)

    def _get_backend_name(self):
        "Return the name of the backend or None if not available."
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
    """Construct a BackendSampler called sampler from the given backend
    parameter, which can be a Sampler, a Backend, a string, or None."""
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
        ibm_provider = Provider()
        ibm_backend = ibm_provider.get_backend(name=backend)
        sampler = BackendSampler(ibm_backend)
    elif backend is None:
        # If nothing was provided, sample from a local simulator.
        sampler = BackendSampler(Aer.get_backend("aer_simulator"))
    else:
        # If none of the above were provided, abort.
        raise ValueError(
            "failed to recognize %s" " as a Qiskit Backend or Sampler" % repr(backend)
        )

    # Specify job tags unless the caller already specified them.
    if "job_tags" not in sampler.options:
        sampler.set_options(job_tags=tags)
    return sampler


def circuit_gen(env, quantum_instance=None):
    # Cost function and single circuit

    ports = env.ports()
    qubo = solver.construct_qubo(env, None)
    # dictionary to hold the ising conversion of the qubo
    isin = {}
    # dictionary to be able to retrieve port numbers
    vardict = {}
    for idx, port in enumerate(ports):
        vardict[port] = idx
    for con in qubo:
        # Add ancillary bits to vardict
        if "_anc" in con[0] or "_anc" in con[1]:
            for c in con:
                # Surely there's a better way to add ancilla bits to vardict, without having to check each constraint...
                if c not in vardict:
                    idx += 1
                    vardict[c] = idx
        # Convert the QUBO to ising
        if con[0] == con[1]:
            if con in isin:
                isin[con] += qubo[con] / 2
            else:
                isin[con] = qubo[con] / 2
        else:
            three = [con, (con[0], con[0]), (con[1], con[1])]
            for c in three:
                if c in isin:
                    isin[c] += qubo[con] / 4
                else:
                    isin[c] = qubo[con] / 4

    siz = idx + 1
    # Coefficient matrix for calculating cost function
    # This matrix still uses the qubo variables: qiskit naturally returns 0 and 1
    mat = np.zeros((siz, siz))
    for con in qubo:
        mat[vardict[con[0]]][vardict[con[1]]] = qubo[con]
    # Quantum Circuit for QAOA
    # regs = []
    # for var in vardict:
    # regs.append(qiskit.QuantumRegister(1, var))
    vardict = {x: qiskit.QuantumRegister(1, x) for x in vardict}
    creg = qiskit.ClassicalRegister(siz)
    qc = qiskit.QuantumCircuit(*[vardict[x] for x in vardict], creg)
    # Parameters to be optimized
    alpha = qiskit.circuit.Parameter("a")
    beta = qiskit.circuit.Parameter("b")

    # Initial state
    qc.h(range(siz))

    # Phase separator uses ising values
    for con in isin:
        if isin[con] == 0.0:
            continue
        a = vardict[con[0]]
        b = vardict[con[1]]
        if a == b:
            qc.rz(-alpha * isin[con], a)
        else:
            qc.rzz(alpha * isin[con], a, b)

    # Universal mixer and measurement
    qc.rx(beta, range(siz))
    for p in range(siz):
        qc.measure(p, p)

    # If there's a quantum_instance given, transpile down to available basis gates
    if quantum_instance:
        qc = qiskit.transpile(
            qc,
            backend=quantum_instance.backend,
            basis_gates=quantum_instance.backend_config["basis_gates"],
            optimization_level=0,
        )

    # Standard cost function; takes counts from qiskit running a circuit.
    # This evaluates every result returned and weights them by the coefficients.
    # For few qubits, this is essentially brute force.
    def ret(counts):
        totval = 0.0
        total = 0.0
        for count in counts:
            arr = np.array([int(x) for x in count], dtype=int)
            totval += counts[count]
            total += counts[count] * (arr.T @ mat @ arr)
        return total / totval

    return qc, ret


def manual_qaoa(
    env,
    backend=None,
    hard_scale=None,
    optimizer="COBYLA",
    reps=1,
    initial_point=None,
    callback=None,
):
    "Solve an NchooseK problem, returning a QiskitResult."
    # TODO Set something up to define this
    shots = 1024
    # Acquire a BackendSampler from the backend parameter and a list
    # of job tags.
    job_tags = ["NchooseK", "nchoosek-%010x" % random.randrange(16**10)]
    sampler = _construct_backendsampler(backend, job_tags)

    # Convert the environment to a QUBO.
    qtime1 = datetime.datetime.now()
    qubo = solver.construct_qubo(env, hard_scale)  # noqa: F841 solely used for QUBO construction timing
    qtime2 = datetime.datetime.now()

    # Keep track of the number of shots and jobs.
    final_shots = 0  # Shots in final job; used for computing tallies
    total_shots = 0  # Total shots across all jobs
    num_jobs = 0  # Number of jobs submitted

    # Run the problem with QAOA.
    stime1 = datetime.datetime.now()
    circ, fun = circuit_gen(env, quantum_instance=None)

    def execute(params):
        nonlocal total_shots, job_ids
        qc = circ.bind_parameters(
            {circ.parameters[i]: params[i] for i in range(len(params))}
        )
        job = sampler.run(qc, nshots=shots)
        counts = job.result().quasi_dists
        job_ids.append(job.job_id)
        total_shots += job.result().metadata[0]["shots"]
        # counts = sampler.run(sampler.circuits[-1], nshots=shots).result().quasi_dists
        counts = {
            format(x, "0" + str(qc.num_qubits) + "b"): counts[0][x] for x in counts[0]
        }
        fun(counts)

    if not initial_point:
        initial_point = [1.0, 1.0]
    options = {"maxiter": 35}
    jac, hess = None, None
    if optimizer == "COBYLA":
        options["rhobeg"] = 1
    elif optimizer == "Nelder-Mead":
        N = len(initial_point)
        first_vertex = np.ones([1, N])
        other_vertices = 2.14 * np.eye(N) + np.ones([N, N])
        simplex = np.concatenate((first_vertex, other_vertices), axis=0)
        options["initial_simplex"] = simplex
        options["return_all"] = True
    else:
        jac = "cs"
        hess = "cs"

    total_shots = 0  # Total shots across all jobs
    job_ids = []

    opt_params = scipy.optimize.minimize(
        execute, initial_point, method=optimizer, options=options, jac=jac, hess=hess
    )
    if isinstance(opt_params, scipy.optimize._optimize.OptimizeResult):
        print("opt_params.x")
        circuit = circ.bind_parameters(
            {circ.parameters[i]: opt_params.x[i] for i in range(len(opt_params.x))}
        )
    else:
        print("opt_params")
        circuit = circ.bind_parameters(
            {circ.parameters[i]: opt_params[i] for i in range(len(opt_params))}
        )
    job = sampler.run(circuit)
    result = job.result()
    stime2 = datetime.datetime.now()
    job_ids.append(job.job_id)
    final_shots = result.metadata[0]["shots"]

    counts = {
        format(x, "0" + str(circuit.num_qubits) + "b"): result.quasi_dists[0][x]
        for x in result.quasi_dists[0]
    }
    # labels = [i.name for i in circuit.qregs]

    ret = QiskitResult()
    ret.variables = env.ports()
    ret.solutions = []
    # vars = result.variables
    # for samp in result.samples:
    for samp in counts:
        ret.solutions.append(
            {
                circuit.qregs[i].name: x != "0"
                for i, x in enumerate(samp)
                if circuit.qregs[i].name in env.ports()
            }
        )

    # Record this time now to ensure that the QAOA is done running first.
    ret.qubo_times = (qtime1, qtime2)
    ret.solver_times = (stime1, stime2)
    ret.sampler = sampler
    # ret.samples = result.samples
    ret.final_shots = final_shots
    ret.total_shots = total_shots
    ret.num_samples = final_shots  # Number actually returned to the caller
    ret.num_jobs = num_jobs
    ret.tallies = [round(counts[s] * ret.final_shots) for s in counts]
    ret.tallies, ret.solutions = (
        list(x)
        for x in zip(*sorted(zip(ret.tallies, ret.solutions), key=lambda pair: pair[0]))
    )
    ret.tallies.reverse()
    ret.solutions.reverse()
    ret.num_jobs = len(job_ids)
    ret.job
    try:
        ret.qubits = max([c.num_qubits for c in sampler.transpiled_circuits])
        ret.depth = max([c.depth() for c in sampler.transpiled_circuits])
    except AttributeError:
        ret.qubits = max([c.num_qubits for c in sampler.circuits])
        ret.depth = max([c.depth() for c in sampler.circuits])
    ret.job_tags = job_tags
    return ret
