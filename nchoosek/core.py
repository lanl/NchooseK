##################################
# NchooseK top-level definitions #
##################################

import nchoosek
from nchoosek.solver.bqm import BQMMixin
import os
import shlex


class UnknownPortError(Exception):
    'An unknown port was referenced.'

    def __init__(self, type_name, port_name):
        self.bad_port = port_name
        if type_name is None:
            msg = 'No port named "%s" exists in the environment' % port_name
        else:
            msg = 'Block type %s does not define a port named "%s"' % \
                (type_name, port_name)
        super().__init__(msg)


class DuplicatePortError(Exception):
    'A supposedly new port already exists.'

    def __init__(self, port_name, block_name=None):
        if block_name is None:
            msg = 'Port "%s" already exists in the environment' % port_name
        else:
            msg = 'Port "%s" appears more than once in blocks of type "%s"' % \
                (port_name, block_name)
        super().__init__(msg)


class Constraint(BQMMixin):
    'Representation of a constraint (k of n ports are True).'

    def __init__(self, port_list, num_true, soft=False):
        self.port_list = list(port_list)  # Ports; can include duplicates
        self.num_true = set(num_true)     # Set of allowable True counts
        self.soft = soft                  # true: allow constraint to be broken

    def __str__(self):
        'Return a constraint as a string.'
        msg = '%s choose %s' % (self.port_list, self.num_true)
        if self.soft:
            msg += ' (soft)'
        return msg


class Block(object):
    'Base class for user-defined NchooseK types.'

    def __init__(self, bindings=None):
        # Assign the object an ID that's unique to the parent environment.
        env = self.env
        self._unique_id = '%s%d' % (self._type_name, env._next_id)
        env._next_id += 1

        # Notify our parent environment of our constraints and our port names.
        if self._constraint is not None:
            lps = self._constraint.port_list
            vals = self._constraint.num_true
            soft = self._constraint.soft
            gps = ['%s.%s' % (self._unique_id, lp) for lp in lps]
            gps_set = set(gps)
            dups = env._port_names & gps_set
            if len(dups) > 0:
                raise DuplicatePortError(dups.pop())
            env._port_names |= gps_set
            env._constraints.append(Constraint(gps, vals, soft))

        # If a list of port bindings was provided, equate those to the
        # global port names.
        if bindings is not None:
            if len(bindings) != len(self._port_list):
                raise ValueError('%d binding(s) were provided for %d port(s)' %
                                 (len(bindings), len(self._port_list)))
            for gp1, gp2 in zip(bindings, [self[p] for p in self._port_list]):
                env.same(gp1, gp2)

    def ports(self, env_globals=False):
        '''Return a list of either local (default) or environment-global
        port names.'''
        if env_globals:
            return ['%s.%s' % (self._unique_id, lp) for lp in self._port_list]
        else:
            return [lp for lp in self._port_list]

    def __getattr__(self, attr):
        'Given a type-local port name, return an environment-global port name.'
        if attr in self._port_list:
            return '%s.%s' % (self._unique_id, attr)
        raise AttributeError(attr)

    def __getitem__(self, key):
        'Given a type-local port name, return an environment-global port name.'
        if key in self._port_list:
            return '%s.%s' % (self._unique_id, key)
        raise KeyError(key)


class Environment(object):
    'A namespace for a set of related NchooseK operations.'

    def __init__(self):
        'Instantiate a new list of constraints.'
        self._constraints = []    # All constraints within this environment
        self._port_names = set()  # All port names within this environment
        self._next_id = 1         # Next available unique ID for an object

    def register_port(self, port_name):
        '''Register a new, environment-global port name.  Return the
        name unmodified.'''
        if port_name in self._port_names:
            raise DuplicatePortError(port_name)
        self._port_names.add(port_name)
        return port_name

    def new_type(self, name, port_list, constraint=None):
        '''Define a new data type, characterized by a type name, a set of
        type-local port names, and a list of constraints.'''
        # Ensure that the given port names are unique.
        port_set = set()
        for lp in port_list:
            if lp in port_set:
                raise DuplicatePortError(lp, name)
            port_set.add(lp)

        # Ensure that all constraints reference only known port names.
        if constraint is not None:
            for lp in constraint.port_list:
                if lp not in port_set:
                    raise UnknownPortError(name, lp)

        # Derive a type from Block and return it.
        return type(name, (Block,), {
            '_type_name': name,
            '_port_list': list(port_list),
            '_constraint': constraint,
            'env': self})

    def same(self, gp1, gp2, soft=False):
        'Declare that two environment-global ports must have the same value.'
        if gp1 not in self._port_names:
            raise UnknownPortError(None, gp1)
        if gp2 not in self._port_names:
            raise UnknownPortError(None, gp2)
        self._constraints.append(Constraint([gp1, gp2], {0, 2}, soft))

    def different(self, gp1, gp2, soft=False):
        'Declare that two environment-global ports must have different values.'
        if gp1 not in self._port_names:
            raise UnknownPortError(None, gp1)
        if gp2 not in self._port_names:
            raise UnknownPortError(None, gp2)
        self._constraints.append(Constraint([gp1, gp2], {1}, soft))

    def minimize(self, gps):
        'Try to set as few environment-global ports to True as possible.'
        for p in gps:
            if p not in self._port_names:
                raise UnknownPortError(None, p)
            self._constraints.append(Constraint([p], {0}, soft=True))

    def maximize(self, gps):
        'Try to set as mant environment-global ports to True as possible.'
        for p in gps:
            if p not in self._port_names:
                raise UnknownPortError(None, p)
            self._constraints.append(Constraint([p], {1}, soft=True))

    def nck(self, gps, vals, soft=False):
        '''Add a new constraint to the environment.  This method accepts
        only environment-global ports, not type-local port names.'''
        for gp in gps:
            if gp not in self._port_names:
                raise UnknownPortError(None, gp)
        self._constraints.append(Constraint(gps, vals, soft))

    def __str__(self):
        'Return an environment as a single string.'
        pstr = ', '.join(sorted(self._port_names))
        cstr = ', '.join([str(c) for c in self._constraints])
        return 'Ports {%s} with constraints {%s}' % (pstr, cstr)

    def ports(self):
        'Return a set of all port names in the environment.'
        return self._port_names

    def constraints(self):
        'Return a set of all constraints in the environment.'
        # Although we store constraints as a list, we return them as a
        # set to reinforce that the order is meaningless.
        return set(self._constraints)

    def solve(self, solver=None, *args, **kwargs):
        'Solve for all constraints in the environment.'
        # Parse key=value pairs in the NCHOOSEK_PARAMS environment variable.
        all_kwargs = {}
        var_params = os.getenv('NCHOOSEK_PARAMS')
        if var_params is not None:
            toks = shlex.split(var_params)
            for t in toks:
                try:
                    # Parse "key=value" into a key and a value.
                    eq = t.index('=')
                    k, v = t[:eq], t[eq+1:]

                    # Attempt to convert value to a number.
                    try:
                        v = int(v)
                    except ValueError:
                        try:
                            v = float(v)
                        except ValueError:
                            pass
                except ValueError:
                    k, v = t, True
                all_kwargs[k] = v

        # Invoke the solver.
        all_kwargs.update(**kwargs)
        solve_func = nchoosek.solve
        if solver is not None:
            solve_func = nchoosek._name_to_solver(solver)
        return solve_func(self, *args, **all_kwargs)

    class Validation(object):
        'Encapsulate the status of a validation check.'

        def __init__(self):
            self.hard_passed = []
            self.hard_failed = []
            self.soft_passed = []
            self.soft_failed = []

    def validation(self, soln):
        '''Return a Validation object that partitions constraints based on
        their pass/fail status.'''
        result = self.Validation()
        for c in self._constraints:
            port_values = [soln[p] for p in c.port_list]
            num_true = sum(port_values)
            if num_true in c.num_true:
                # Pass
                if c.soft:
                    result.soft_passed.append(c)
                else:
                    result.hard_passed.append(c)
            else:
                # Fail
                if c.soft:
                    result.soft_failed.append(c)
                else:
                    result.hard_failed.append(c)
        return result

    def valid(self, soln):
        'Return True if all hard constraints are satisfied, False otherwise.'
        raw = self.validation(soln)
        return len(raw.hard_failed) == 0

    def quality(self, soln):
        '''Return the number of soft constraints which passed and the total
        number of soft constraints.'''
        raw = self.validation(soln)
        soft = len(raw.soft_passed)
        total = soft + len(raw.soft_failed)
        return soft, total
