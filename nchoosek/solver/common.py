#########################################
# Define classes and functions that are #
# common across multiple solvers        #
#########################################

from collections import defaultdict
import qiskit
import numpy as np
import math
import cmath


class ConstraintConversionError(Exception):
    'A constraint could not be converted to a QUBO.'

    def __init__(self, c):
        msg = 'failed to convert constraint to a QUBO: %s' % str(c)
        super().__init__(msg)


def rename_ancilla(name, inc):
    'Rename _ancN with _anc(N+inc).'
    if name[:4] != '_anc':
        return name
    num = int(name[4:])
    return '_anc%d' % (num + inc)


def construct_qubo(env, hard_scale):
    'Convert an entire environment to a QUBO.'
    # Convert each constraint to an independent QUBO.
    cons2qubo = {}
    have_soft = False
    for c in env.constraints():
        qqv, _, objs = c.solve_qubo()
        if qqv is None:
            raise ConstraintConversionError(str(c))
        cons2qubo[c] = (qqv, objs)
        have_soft = have_soft or c.soft

    # Find the minimum hard-constraint gap and maximum soft-constraint gap.
    # Scale hard constraints to make it more valuable to violate all soft
    # constraints than a single hard constraint.
    if hard_scale is None and have_soft:
        min_hard = 2**30
        sum_max_soft = 0
        for c, (_, objs) in cons2qubo.items():
            if c.soft:
                sum_max_soft += objs[-1] - objs[0]
            else:
                min_hard = min(min_hard, objs[1] - objs[0])
        hard_scale = sum_max_soft/min_hard + 1.0
    if hard_scale is None:
        hard_scale = 1.0

    # Merge all constraints into a single, large QUBO.
    qubo = defaultdict(lambda: 0)
    total_anc = 0   # Total number of ancillae across all constraints
    for c, (qqv, _) in cons2qubo.items():
        for q1, q2, val in qqv:
            if not c.soft:
                val *= hard_scale
            q1 = rename_ancilla(q1, total_anc)
            q2 = rename_ancilla(q2, total_anc)
            qubo[(q1, q2)] += val
        total_anc += len({a
                          for q1, q2, _ in qqv
                          for a in [q1, q2]
                          if a[:4] == '_anc'})
    return qubo


class Result():
    'Encapsulate solver results and related data.'

    def __init__(self):
        self.variables = None
        self.solutions = None
        self.tallies = None
        self.qubits = None
        self.qubo_times = None
        self.solver_times = None

    def _repr_dict(self):
        'Return a dictionary for use internally by __repr__.'
        ret = {}
        if self.variables:
            ret["variables"] = self.variables
        if self.solutions:
            ret["solutions"] = self.solutions
        if self.tallies:
            ret["tallies"] = self.tallies
        if self.qubits:
            ret["number of qubits"] = self.qubits
        if self.qubo_times:
            ret["qubo times"] = self.solver_times
        if self.solver_times:
            ret["solver times"] = self.solver_times
        return ret

    def __repr__(self):
        ret = self._repr_dict()
        return 'nchoosek.solver.Result(%s)' % str(ret)

    def _str_dict(self):
        'Return a dictionary for use internally by __str__.'
        ret = {}
        if self.variables:
            ret["number of variables"] = len(self.variables)
        if self.solutions:
            ret["top solution"] = self.solutions[0]
            ret["number of solutions"] = len(self.solutions)
        if self.tallies:
            ret["top solution tallies"] = self.tallies[0]
        if self.qubits:
            ret["number of qubits"] = self.qubits
        if self.qubo_times:
            ret["qubo times"] = (self.qubo_times[0].strftime("%Y-%m-%d %H:%M:%S.%f"),
                                 self.qubo_times[1].strftime("%Y-%m-%d %H:%M:%S.%f"))
        if self.solver_times:
            ret["solver times"] = (self.solver_times[0].strftime("%Y-%m-%d %H:%M:%S.%f"),
                                   self.solver_times[1].strftime("%Y-%m-%d %H:%M:%S.%f"))
        return ret

    def __str__(self):
        ret = self._str_dict()
        return str(ret)

def z1(qc, qubit, coef):
    # i = 0 + 1j
    # fac = i*math.pi/2
    qc.rz(-coef, qubit)
    # qc.unitary([[cmath.exp(coef*fac), 0], [0, cmath.exp(-1*coef*fac)]], qubit)

def z2(qc, qubits, coef):
    qc.rzz(coef, qubits[0], qubits[1])

def circuit_gen(env, quantum_instance=None):
    # Cost function and single circuit

    qubo = construct_qubo(env, None)
    vardict = {}
    ports = env.ports()
    mat = np.zeros((len(ports), len(ports)))
    for idx, port in enumerate(ports):
        vardict[port] = idx
    qc = qiskit.QuantumCircuit(len(ports), len(ports))
    qc.h(range(len(ports)))
    alpha = qiskit.circuit.Parameter('a')
    beta = qiskit.circuit.Parameter('b')
    for con in qubo:
        a = vardict[con[0]]
        b = vardict[con[1]]
        if a == b:
            z1(qc, a, alpha*qubo[con])
        else:
            z2(qc, [a, b], alpha*qubo[con])
        mat[a][b] = qubo[con]
    qc.rx(beta, range(len(ports)))
    for p in range(len(ports)):
        qc.measure(p, p)
    
    if quantum_instance:
        qc = qiskit.transpile(qc, backend=quantum_instance.backend, basis_gates=quantum_instance.backend_config["basis_gates"], optimization_level=0)
    
    def ret(counts):
        totval = 0
        total = 0
        for count in counts:
            arr = np.array([int(x) for x in count], dtype=int)
            totval += counts[count]
            total += counts[count]*(arr.T @ mat @ arr)
        return total/totval

    return qc, ret
