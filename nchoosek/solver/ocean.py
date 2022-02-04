########################################
# Use D-Wave Ocean to solve for the    #
# variables in an NchooseK environment #
########################################

from dwave.system import DWaveSampler, EmbeddingComposite
from nchoosek.solver import construct_qubo


def solve(env, sampler=None, hard_scale=None, **sampler_args):
    'Solve for the variables in a given NchooseK environment.'
    # Create a sampler if one wasn't provided.
    if sampler is None:
        sampler = EmbeddingComposite(DWaveSampler())

    # Convert the environment to a QUBO.
    qubo = construct_qubo(env, hard_scale)

    # Solve the QUBO using the given sampler.
    result = sampler.sample_qubo(qubo, **sampler_args)

    # Convert the result to a mapping from port names to Booleans and
    # return it.
    ports = env.ports()
    return {k: v != 0 for k, v in result.first.sample.items() if k in ports}
