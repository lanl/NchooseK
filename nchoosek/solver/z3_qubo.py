# ####################################################
# Use the Z3 Theorem Prover to solve classically for #
# the variables in an NchooseK environment, first    #
# converting the environment to a QUBO               #
######################################################

import z3
from collections import defaultdict


class ConstraintConversionError(Exception):
    'A constraint could not be converted to a QUBO.'

    def __init__(self, c):
        msg = 'failed to convert constraint to a QUBO: %s' % str(c)
        super().__init__(msg)


def solve(env, hard_scale=None):
    'Solve for the variables in a given NchooseK environment.'
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
    for c in env.constraints():
        qqv, _ = c.solve_qubo()
        if qqv is None:
            raise ConstraintConversionError(str(c))
        for q1, q2, val in qqv:
            if not c.soft:
                val *= hard_scale
            qubo[(q1, q2)] += val

    # Constrain all QUBO variables to be either 0 or 1.
    all_vars = {e for qs in qubo for e in qs}
    s = z3.Optimize()
    nck_to_z3 = {gp: z3.Int(gp) for gp in all_vars}
    for v in nck_to_z3.values():
        s.add(v >= 0, v <= 1)

    # Minimize the sum of all constraints in the QUBO.
    obj = 0
    for (q0, q1), wt in qubo.items():
        if q0 == q1:
            # Linear constraints
            obj += wt*nck_to_z3[q0]
        else:
            obj += wt*nck_to_z3[q0]*nck_to_z3[q1]
    s.minimize(obj)

    # Minimize the objective function subject to the constraints, and
    # return a dictionary mapping port names to Boolean values.
    if s.check() != z3.sat:
        return None
    model = s.model()
    ports = env.ports()
    return {k: bool(model[v].as_long())
            for k, v in nck_to_z3.items()
            if k in ports}
