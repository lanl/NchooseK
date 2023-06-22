########################################
# Use D-Wave Ocean to solve for the    #
# variables in an NchooseK environment #
########################################

import copy
import datetime
import warnings
import dimod
from dwave.system import DWaveSampler, EmbeddingComposite
from nchoosek import solver
from nchoosek.solver import construct_qubo


class OceanResult(solver.Result):
    'Add Ocean-specific fields to a Result.'

    def __init__(self):
        super().__init__()
        self.energies = None
        self.sampler = None
        self.exec_info = None

    @staticmethod
    def _innermost_sampler(s):
        'Drill down to the innermost sampler.'
        try:
            return s.child
        except AttributeError:
            return s

    def _sampler_properties(self, shorten=False):
        'Return all sampler properties with values optionally shortened.'
        props = {}
        sampler = self._innermost_sampler(self.sampler)
        for k, v in sampler.properties.items():
            props[k] = v
            if shorten and not isinstance(v, str):
                try:
                    n = len(v)
                    if n > 10:
                        props[k] = '[%d entries]' % n
                except TypeError:
                    pass
        return props

    @staticmethod
    def _sampler_name(s, shorten=False):
        "Return a sampler's name."
        if shorten:
            return s.__class__.__name__
        return s

    def _sampler_hierarchy(self, samp, shorten=False):
        'Return a tree of samplers.'
        tree = [self._sampler_name(samp, shorten)]
        try:
            for s in samp.children:
                tree.append(self._sampler_hierarchy(s, shorten))
        except AttributeError:
            pass
        return tree

    def __repr__(self):
        ret = self._repr_dict()
        ret['Ocean sampler'] = self._sampler_hierarchy(self.sampler, False)
        ret["Ocean sampler properties"] = self._sampler_properties(False)
        ret["Ocean execution information"] = self.exec_info
        return 'nchoosek.solver.Result(%s)' % str(ret)

    def __str__(self):
        ret = self._str_dict()
        ret['Ocean sampler'] = self._sampler_hierarchy(self.sampler, True)
        ret["Ocean sampler properties"] = self._sampler_properties(True)
        exec_info = copy.deepcopy(self.exec_info)
        try:
            exec_info['embedding_context']['embedding'] = '[%d entries]' % \
                len(exec_info['embedding_context']['embedding'])
        except KeyError:
            pass
        ret["Ocean execution information"] = exec_info
        return str(ret)


def solve(env, sampler=None, hard_scale=None, **sampler_args):
    'Solve for the variables in a given NchooseK environment.'
    # Create a sampler if one wasn't provided.
    if sampler is None:
        sampler = EmbeddingComposite(DWaveSampler())

    # Convert the environment to a QUBO.
    qtime1 = datetime.datetime.now()
    qubo = construct_qubo(env, hard_scale)
    qtime2 = datetime.datetime.now()

    # Remove arguments that the sampler doesn't recognize.
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore')
        try:
            kwargs = sampler_args.copy()
            kwargs['return_embedding'] = True
            kwargs = sampler.remove_unknown_kwargs(**sampler_args)
        except dimod.exceptions.SamplerUnknownArgWarning:
            pass

    # Solve the QUBO using the given sampler.
    stime1 = datetime.datetime.now()
    result = sampler.sample_qubo(qubo, **kwargs)
    stime2 = datetime.datetime.now()

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
    ret = OceanResult()
    ret.variables = env.ports()
    ret.solutions = res
    ret.qubo_times = (qtime1, qtime2)
    ret.solver_times = (stime1, stime2)
    ret.tallies = num
    ret.energies = en
    ret.sampler = sampler
    ret.exec_info = result.info
    ret.num_samples = sum(num)

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
