########################################
# Use D-Wave Ocean to solve for the    #
# variables in an NchooseK environment #
########################################

from dwave.system import DWaveSampler, EmbeddingComposite
from collections import defaultdict

class ConstraintConversionError(Exception):
    'A constraint could not be converted to a QUBO.'

    def __init__(self, c):
        msg = 'failed to convert constraint to a QUBO: %s' % str(c)
        super().__init__(msg)

def solve(env, sampler=None, hard_scale=10, **sampler_args):
    'Solve for the variables in a given NchooseK environment.'
    # Create a sampler if one wasn't provided.
    if sampler == None:
        sampler = EmbeddingComposite(DWaveSampler())

    # Merge all constraints into a single, large QUBO.
    qubo = defaultdict(lambda: 0)
    for c in env.constraints():
        qqv, _ = c.solve_qubo()
        if qqv == None:
            raise ConstraintConversionError(str(c))
        for q1, q2, val in qqv:
            if not c.soft:
                val *= hard_scale
            qubo[(q1, q2)] += val

    # Solve the QUBO using the given sampler.
    result = sampler.sample_qubo(qubo, **sampler_args)

    # Convert the result to a mapping from port names to Booleans and return it.
    ports = env.ports()
    return {k: v != 0 for k, v in result.first.sample.items() if k in ports}
