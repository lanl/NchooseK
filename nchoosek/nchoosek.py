##################################
# NchooseK top-level definitions #
##################################

class UnknownPortError(Exception):
    "An unknown port was referenced."

    def __init__(self, type_name, port_name):
        self.bad_port = port_name
        if type_name == None:
            msg = 'No port named "%s" exists in the environment' % port_name
        else:
            msg = 'Block type %s does not define a port named "%s"' % (type_name, port_name)
        super().__init__(msg)

class Block(object):
    "Base class for user-defined NchooseK types."

    def __init__(self):
        # Assign the object an ID that's unique to the parent environment.
        env = self.env
        self._unique_id = "%s%d" % (self._type_name, env._next_id)
        env._next_id += 1

        # Notify our parent environment of our constraints and our port names.
        for lps, vals in self.type_constraints:
            gps = ["%s.%s" % (self._unique_id, lp) for lp in lps]
            env._port_names |= set(gps)
            env._constraints.append((gps, vals))

    def __getattr__(self, attr):
        "Given a type-local port name, return an environment-global port name."
        if attr in self.port_names:
            return "%s.%s" % (self._unique_id, attr)
        raise AttributeError(attr)

class Env(object):
    "A namespace for a set of related NchooseK operations."

    def __init__(self):
        "Instantiate a new list of constraints."
        self._constraints = []    # All constraints within this environment
        self._port_names = set()  # All port names within this environment
        self._next_id = 1         # Next available unique ID for an object

    def make_type(self, name, port_names, constraints=[]):
        """Define a new data type, characterized by a type name, a set of
        port names, and a list of constraints."""
        # Ensure that all constraints reference only known port names.
        port_set = set(port_names)
        for lps, vals in constraints:
            for lp in lps:
                if lp not in port_names:
                    raise UnknownPortError(name, lp)

        # Derive a type from Block and return it.
        return type(name, (Block,), {
            "_type_name": name,
            "port_names": port_set,
            "type_constraints": constraints,
            "env": self})

    def nck(self, gps, vals):
        """Add a new constraint to the environment.  This method accepts
        only environment-globsl ports, not type-local port names."""
        for gp in gps:
            if gp not in self._port_names:
                raise UnknownPortError(None, gp)
        self._constraints.append((gps, vals))
