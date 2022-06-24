########################################
# Use D-Wave Ocean to solve for the    #
# variables in an NchooseK environment #
########################################

import datetime
from dwave.system import DWaveSampler, EmbeddingComposite
from nchoosek import solver
from nchoosek.solver import construct_qubo


def solve(env, sampler=None, hard_scale=None, **sampler_args):
    'Solve for the variables in a given NchooseK environment.'
    # Create a sampler if one wasn't provided.
    if sampler is None:
        sampler = EmbeddingComposite(DWaveSampler())

    # Convert the environment to a QUBO.
    qubo = construct_qubo(env, hard_scale)

    time1 = datetime.datetime.now()
    # Solve the QUBO using the given sampler.
    ret = solver.Result()
    result = sampler.sample_qubo(qubo, return_embedding=True, **sampler_args)

    # Convert the result to a mapping from port names to Booleans and
    # record it, the number of occurences, and the energies.
    ports = env.ports()
    res = []
    num = []
    en = []
    for it in result.data():
        res.append({k: v != 0 for k, v in it.sample.items() if k in ports})
        num.append(it.num_occurrences)
        en.append(it.energy)
    ret.solutions = res
    time2 = datetime.datetime.now()
    ret.times = (time1, time2)
    ret.tallies = num
    ret.energies = en

    # Inspect the embedding to find out how many qubits were used.
    # Simulators will not have embedding_context so we assume no
    # additional qubits were required.
    try:
        embed = result.info['embedding_context']['embedding']
        nqubs = 0
        for chain in embed.values():
            nqubs += len(chain)
    except KeyError:
        nqubs = len(ports)
    ret.qubits = nqubs

    return ret
