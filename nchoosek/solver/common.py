#########################################
# Define classes and functions that are #
# common across multiple solvers        #
#########################################

from collections import defaultdict


class ConstraintConversionError(Exception):
    'A constraint could not be converted to a QUBO.'

    def __init__(self, c):
        msg = 'failed to convert constraint to a QUBO: %s' % str(c)
        super().__init__(msg)


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
    for c in env.constraints():
        qqv, _ = c.solve_qubo()
        if qqv is None:
            raise ConstraintConversionError(str(c))
        for q1, q2, val in qqv:
            if not c.soft:
                val *= hard_scale
            qubo[(q1, q2)] += val
    return qubo
