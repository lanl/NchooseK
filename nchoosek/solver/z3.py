######################################
# Use the Z3 Theorem Prover to solve #
# classically for the variables in   #
# an NchooseK environment            #
######################################

import z3


def solve(env):
    'Solve for the variables in a given NchooseK environment.'
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
    return {k: bool(model[v].as_long()) for k, v in nck_to_z3.items()}
