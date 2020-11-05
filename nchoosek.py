##################################
# NchooseK top-level definitions #
##################################

class UnknownPortError(Exception):
    "An unknown port was referenced."

    def __init__(self, type_name, port_name):
        self.bad_port = port_name
        super().__init__('Block type %s does not define a port named "%s"' % (type_name, port_name))

class Block(object):
    "Base class for user-defined NchooseK types."

    def __init__(self):
        # Assign the object an ID that's unique to the parent environment.
        self._unique_id = "%s%d" % (self._type_name, self.env._next_id)
        self.env._next_id += 1

        # Notify our parent environment of our constraints.
        for lps, vals in self.type_constraints:
            gps = ["%s.%s" % (self._unique_id, lp) for lp in lps]
            self.env._constraints.append((gps, vals))

class Env(object):
    "A namespace for a set of related NchooseK operations."
    
    def __init__(self):
        "Instantiate a new list of constraints."
        self._constraints = []  # All constraints within this environment
        self._next_id = 1       # Next available unique ID for an object

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
