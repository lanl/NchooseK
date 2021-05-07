##################################
# NchooseK top-level definitions #
##################################

class UnknownPortError(Exception):
    'An unknown port was referenced.'

    def __init__(self, type_name, port_name):
        self.bad_port = port_name
        if type_name == None:
            msg = 'No port named "%s" exists in the environment' % port_name
        else:
            msg = 'Block type %s does not define a port named "%s"' % (type_name, port_name)
        super().__init__(msg)

class DuplicatePortError(Exception):
    'A supposedly new port already exists.'

    def __init__(self, port_name):
        super().__init__('Port "%s" already exists in the environment' % port_name)

class Block(object):
    'Base class for user-defined NchooseK types.'

    def __init__(self, bindings=None):
        # Assign the object an ID that's unique to the parent environment.
        env = self.env
        self._unique_id = '%s%d' % (self._type_name, env._next_id)
        env._next_id += 1

        # Notify our parent environment of our constraints and our port names.
        for lps, vals in self.type_constraints:
            gps = ['%s.%s' % (self._unique_id, lp) for lp in lps]
            gps_set = set(gps)
            dups = env._port_names & gps_set
            if len(dups) > 0:
                raise DuplicatePortError(dups.pop())
            env._port_names |= gps_set
            env._constraints.append((gps, vals))

        # If a list of port bindings was provided, equate those to the
        # global port names.
        if bindings != None:
            if len(bindings) != len(self.port_names):
                raise ValueError('%d binding(s) were provided for %d port(s)' % (len(bindings), len(self.port_names)))
            for gp1, gp2 in zip(bindings, [self[p] for p in self.port_names]):
                env.same(gp1, gp2)

    def __getattr__(self, attr):
        'Given a type-local port name, return an environment-global port name.'
        if attr in self.port_names:
            return '%s.%s' % (self._unique_id, attr)
        raise AttributeError(attr)

    def __getitem__(self, key):
        'Given a type-local port name, return an environment-global port name.'
        if key in self.port_names:
            return '%s.%s' % (self._unique_id, key)
        raise KeyError(key)

class Env(object):
    'A namespace for a set of related NchooseK operations.'

    def __init__(self):
        'Instantiate a new list of constraints.'
        self._constraints = []    # All constraints within this environment
        self._port_names = set()  # All port names within this environment
        self._next_id = 1         # Next available unique ID for an object

    def new_port(self, port_name):
        'Define a new, top-level port name.'
        if port_name in self._port_names:
            raise DuplicatePortError(port_name)
        self._port_names.add(port_name)
        return port_name

    def new_type(self, name, port_names, constraints=[]):
        '''Define a new data type, characterized by a type name, a set of
        type-local port names, and a list of constraints.'''
        # Ensure that all constraints reference only known port names.
        port_set = set(port_names)
        for lps, vals in constraints:
            for lp in lps:
                if lp not in port_names:
                    raise UnknownPortError(name, lp)

        # Derive a type from Block and return it.
        return type(name, (Block,), {
            '_type_name': name,
            'port_names': list(port_names),
            'type_constraints': constraints,
            'env': self})

    def same(self, gp1, gp2):
        'Declare that two environment-global ports must have the same value.'
        if gp1 not in self._port_names:
            raise UnknownPortError(None, gp1)
        if gp2 not in self._port_names:
            raise UnknownPortError(None, gp2)
        self._constraints.append((set([gp1, gp2]), [0, 2]))

    def different(self, gp1, gp2):
        'Declare that two environment-global ports must have different values.'
        if gp1 not in self._port_names:
            raise UnknownPortError(None, gp1)
        if gp2 not in self._port_names:
            raise UnknownPortError(None, gp2)
        self._constraints.append((set([gp1, gp2]), [1]))

    def nck(self, gps, vals):
        '''Add a new constraint to the environment.  This method accepts
        only environment-globsl ports, not type-local port names.'''
        for gp in gps:
            if gp not in self._port_names:
                raise UnknownPortError(None, gp)
        self._constraints.append((gps, vals))
