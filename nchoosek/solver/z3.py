######################################
# Use the Z3 Theorem Prover to solve #
# classically for the variables in   #
# an NchooseK environment            #
######################################

from nchoosek.solver import construct_qubo
import z3


def direct_solve(env):
    '''Solve for the variables in a given NchooseK environment by expressing
    each constraint directly in Z3.'''
    # Constrain all ports to be either 0 or 1.
    s = z3.Optimize()
    nck_to_z3 = {gp: z3.Int(gp) for gp in env.ports()}
    for v in nck_to_z3.values():
        s.add(v >= 0, v <= 1)

    # Express each constraint with Z3.
    for i, c in enumerate(env.constraints()):
        ps = [nck_to_z3[p] for p in c.port_list]
        nts = c.num_true
        if c.soft:
            adder = s.add_soft
        else:
            adder = s.add
        if len(nts) == 1:
            # Single k value
            adder(z3.Sum(ps) == list(nts)[0])
        else:
            # Multiple k values
            disj = z3.BoolVector('disj%d' % i, len(nts))
            for i, nt in enumerate(nts):
                disj[i] = z3.Sum(ps) == nt
            adder(z3.Or(disj))

    # Solve the system of constraints, and return a dictionary mapping port
    # names to Boolean values.
    if s.check() != z3.sat:
        return None
    model = s.model()
    ret = env.Result()
    ret.solutions = [{k: bool(model[v].as_long()) for k, v in nck_to_z3.items()}]
    return ret


def qubo_solve(env, hard_scale):
    '''Solve for the variables in a given NchooseK environment by first
    expressing the constraints as a QUBO then converting that to Z3 for
    solution.'''
    # Convert the environment to a QUBO.
    qubo = construct_qubo(env, hard_scale)

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
            # Quadratic constraints
            obj += wt*nck_to_z3[q0]*nck_to_z3[q1]
    s.minimize(obj)

    # Minimize the objective function subject to the constraints, and
    # return a dictionary mapping port names to Boolean values.
    if s.check() != z3.sat:
        return None
    model = s.model()
    ports = env.ports()
    ret = env.Result()
    ret.solutions = [{k: bool(model[v].as_long()) for k, v in nck_to_z3.items()}]
    return ret


def solve(env, qubo=False, hard_scale=None):
    'Solve for the variables in a given NchooseK environment.'
    if qubo:
        return qubo_solve(env, hard_scale)
    else:
        return direct_solve(env)
