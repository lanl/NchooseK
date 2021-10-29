########################################
# Helper routines for NchooseK solvers #
# that convert constraints to binary   #
# quadratic models                     #
########################################

from collections import defaultdict
import itertools
import z3


class BQMMixin(object):
    'Mixin for an nchoosek.Constraint that converts the Constraint to a BQM'

    def _truth_table(self):
        "Convert a Constraint's ports to a truth table."
        # Tally the occurrences of each port name.
        port_tally = defaultdict(lambda: 0)
        for c in self.port_list:
            port_tally[c] += 1

        # Map each column number to a {port name, tally} pair.
        col_info = [(p, port_tally[p])
                    for i, p in enumerate(sorted(port_tally))]

        # Return a truth table containing one column per unique port
        # name plus the per-column name and tally information
        tt = itertools.product(*[[0, 1]]*len(port_tally))
        return list(tt), col_info

    def _solve_ancillae(self, tt, col_info, na):
        'Solve for QUBO coefficients given a number of ancillae.'
        nc = len(col_info)     # Number of columns, no ancillae
        tnc = nc + na          # Total number of columns including ancillae

        # Create a Z3 solver.
        s = z3.Solver()

        # Declare a Z3 variable for each coefficient and for a constant that
        # each valid row must either equal and each invalid row must exceed.
        cf = []
        for i in range(tnc):
            cf.append(z3.Int('a_%d' % i))
        for i in range(tnc - 1):
            for j in range(i + 1, tnc):
                cf.append(z3.Int('b_%d_%d' % (i, j)))
        const = z3.Int('k')

        # Consider in turn each row of the truth table.
        for row in tt:
            # Construct a Z3 expression for each combination of ancillae for
            # this row.
            exprs = []
            for anc in itertools.product(*[[0, 1]]*na):
                ext_row = list(row) + list(anc)
                e = 0
                for i in range(tnc):
                    e += cf[i]*ext_row[i]
                idx = tnc
                for i in range(tnc - 1):
                    for j in range(i + 1, tnc):
                        e += cf[idx]*ext_row[i]*ext_row[j]
                        idx += 1
                exprs.append(z3.simplify(e))

            # Determine if the row honors the constraints.
            valid = sum([b*col_info[i][1]
                         for i, b in enumerate(row)]) in self.num_true
            if valid:
                # Valid row: exactly one ancilla combination results in a
                # ground state; the rest result in an excited state.
                s.add(z3.PbEq([(e == const, 1) for e in exprs], 1))
                s.add(z3.PbEq([(e > const, 1) for e in exprs], len(exprs) - 1))
            else:
                # Invalid row: all ancilla combinations result in an excited
                # state.
                for e in exprs:
                    s.add(e > const)

        # Solve the Z3 model.
        if s.check() != z3.sat:
            return None
        model = s.model()

        # Convert the model to a QUBO, represented as a list of (port1, port2,
        # coefficient) triplets.  For linear terms, port1 == port2.
        qubo = []
        port_names = [ci[0]
                      for ci in col_info] + ['_anc%d' % (i + 1)
                                             for i in range(na)]
        for i in range(tnc):
            nm = port_names[i]
            val = model[cf[i]].as_long()
            qubo.append((nm, nm, val))
        idx = tnc
        for i in range(tnc - 1):
            for j in range(i + 1, tnc):
                val = model[cf[idx]].as_long()
                qubo.append((port_names[i], port_names[j], val))
                idx += 1
        return qubo

    def solve_qubo(self):
        '''Try increasing numbers of ancillae until the truth table can be
        expressed in terms of a QUBO's linear and quadratic coefficients.'''
        tt, col_info = self._truth_table()
        nc = len(col_info)
        for na in range(0, nc):
            soln = self._solve_ancillae(tt, col_info, na)
            if soln is not None:
                return soln, na
        return None, na
