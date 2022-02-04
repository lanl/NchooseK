########################################
# Use D-Wave Ocean to solve for the    #
# variables in an NchooseK environment #
########################################

from dwave.system import DWaveSampler, EmbeddingComposite
from collections import defaultdict
from nchoosek.solver import ConstraintConversionError


def solve(env, sampler=None, hard_scale=None, **sampler_args):
    'Solve for the variables in a given NchooseK environment.'
    # Create a sampler if one wasn't provided.
    if sampler is None:
        sampler = EmbeddingComposite(DWaveSampler())

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

    # Solve the QUBO using the given sampler.
    result = sampler.sample_qubo(qubo, **sampler_args)

    # Convert the result to a mapping from port names to Booleans and
    # return it.
    ports = env.ports()
    return {k: v != 0 for k, v in result.first.sample.items() if k in ports}
