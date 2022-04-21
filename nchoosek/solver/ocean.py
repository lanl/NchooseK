########################################
# Use D-Wave Ocean to solve for the    #
# variables in an NchooseK environment #
########################################

from dwave.system import DWaveSampler, EmbeddingComposite
import dwave.inspector
from nchoosek.solver import construct_qubo


def solve(env, sampler=None, hard_scale=None, **sampler_args):
    'Solve for the variables in a given NchooseK environment.'
    # Create a sampler if one wasn't provided.
    if sampler is None:
        sampler = EmbeddingComposite(DWaveSampler())

    # Convert the environment to a QUBO.
    qubo = construct_qubo(env, hard_scale)

    # Solve the QUBO using the given sampler.
    ret = env.Result()
    result = sampler.sample_qubo(qubo, **sampler_args)

    # Convert the result to a mapping from port names to Booleans and
    # return it.
    ports = env.ports()
    res = []
    num = []
    en = []
    for it in result.data():
        res.append({k: v != 0 for k, v in it.sample.items() if k in ports})
        num.append(it.num_occurrences)
        en.append(it.energy)
    ret.energies = en
    ret.solutions = res
    ret.tallies = num

    # Insepct the embedding to find out how many qubits were used
    # Simulators will not have embedding_context even using dwave.inspector
    try:
        embed = result.info['embedding_context']['embedding']
        nqubs = 0
        for chain in embed.values():
            nqubs += len(chain)
    except KeyError:
        nqubs = len(ports)
    ret.qubits = nqubs

    return ret
