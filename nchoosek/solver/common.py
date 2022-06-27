#########################################
# Define classes and functions that are #
# common across multiple solvers        #
#########################################

from collections import defaultdict
import re


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
    # Scale the weight of hard constraints by either a user-specified
    # value or by an amount greater than the total weight of all soft
    # constraints.
    if hard_scale is None:
        # A hard constraint is worth 1 more than all soft constraints combined.
        hard_scale = 1
        for c in env.constraints():
            if c.soft:
                hard_scale += 1

    # Merge all constraints into a single, large QUBO.
    qubo = defaultdict(lambda: 0)
    total_anc = 0   # Total number of ancillae across all constraints
    for c in env.constraints():
        qqv, _ = c.solve_qubo()
        if qqv is None:
            raise ConstraintConversionError(str(c))
        for q1, q2, val in qqv:
            if not c.soft:
                val *= hard_scale
            q1 = rename_ancilla(q1, total_anc)
            q2 = rename_ancilla(q2, total_anc)
            qubo[(q1, q2)] += val
        total_anc += len({a for a in [q1, q2] if a[:4] == '_anc'})
    return qubo


class Result(object):
    'Encapsulate solver results and related data.'

    def __init__(self):
        self.solutions = None
        self.tallies = None
        self.energies = None
        self.jobIDs = None
        self.qubits = None
        self.depth = None
        self.times = None
        self.quantum_instance = None

    def __repr__(self):
        ret = {}
        if self.solutions:
            ret["top solution"] = self.solutions[0]
            ret["number of solutions"] = len(self.solutions)
        if self.tallies:
            ret["top solution tallies"] = self.tallies[0]
        if self.energies:
            ret["top solution energy"] = self.energies[0]
        if self.qubits:
            ret["qubits"] = self.qubits
        if self.depth:
            ret["depth"] = self.depth
        if self.times:
            ret["times"] = (self.times[0].strftime("%Y-%m-%d %H:%M:%S.%f"),
                            self.times[1].strftime("%Y-%m-%d %H:%M:%S.%f"))
        if self.quantum_instance:
            ret["Qiskit backend"] = self.quantum_instance.backend
        return str(ret)

    def details(self):
        if self.quantum_instance:
            try:
                device = self.quantum_instance.backend
                jobs = device.jobs(limit=50,
                                   start_datetime=self.times[0],
                                   end_datetime=self.times[1])
                qasm = jobs[2].circuits()[0].qasm()
                count = 0
                # Qiskit jobs don't tell you how many physical qubits get used;
                # we need to search through the final qasm.
                for i in range(device.configuration().n_qubits):
                    if re.search(r"cx[^;]*q\[" + str(i) + r"\]", qasm) or \
                       re.search(r"rz\([^\(]*\) q\[" + str(i) + r"\]", qasm):
                        count += 1

                self.jobIDs = []
                for job in jobs:
                    self.jobIDs.append(job.job_id())
                self.qubits = count
                self.depth = jobs[2].circuits()[0].depth()
            except AttributeError:
                # Qiskit's local simulator lacks a jobs field.
                pass
