########################################
# Helper routines for NchooseK solvers #
# that convert constraints to binary   #
# quadratic models                     #
########################################

from collections import defaultdict
import sqlite3
import json
import itertools
import os
import random
import z3


class QUBOCache():
    'Keep track of previously computed QUBOs.'

    def __init__(self):
        db_name = os.getenv('NCHOOSEK_QUBO_CACHE')
        if db_name is None:
            # Cache values in memory only.
            self._qubo_cache = {}  # Map from column info to a QUBO
        else:
            # Create/open an on-disk database.
            self._sql_con = sqlite3.connect(db_name, timeout=60)
            self._sql_cur = self._sql_con.cursor()
            try:
                self._sql_cur.execute('''\
CREATE TABLE qubo_cache (
    var_coll text NOT NULL,
    sel_set text NOT NULL,
    qubo text NOT NULL,
    num_ancillae int NOT NULL,
    obj_vals text NOT NULL,
    PRIMARY KEY (var_coll, sel_set)
)
''')
                self._sql_con.commit()
            except sqlite3.OperationalError:
                pass

    def __del__(self):
        try:
            # On-disk database
            self._sql_con.close()
        except AttributeError:
            # In-memory database
            pass

    def __getitem__(self, key):
        col_info, num_true = key
        sorted_info = sorted(col_info, key=lambda k: (k[1], k[0]))
        vars2vs = {var[0]: 'v%d' % i for i, var in enumerate(sorted_info)}
        key1 = json.dumps(sorted([(vars2vs[var], cnt)
                                  for var, cnt in col_info]))
        key2 = json.dumps(sorted(num_true))
        try:
            # On-disk database
            query_result = self._sql_cur.execute('''\
SELECT qubo, num_ancillae, obj_vals FROM qubo_cache
WHERE var_coll = ? AND sel_set = ?
''', (key1, key2))
            found = query_result.fetchone()
            if found is None:
                raise KeyError('Column information not found')
            qubo = json.loads(found[0])
            na = found[1]
            objs = json.loads(found[2])
        except AttributeError:
            # In-memory database
            qubo, na, objs = json.loads(self._qubo_cache[(key1, key2)])
        vs2vars = {'v%d' % i: var[0] for i, var in enumerate(sorted_info)}
        soln = [(vs2vars.setdefault(v1, v1),
                 vs2vars.setdefault(v2, v2),
                 wt)
                for v1, v2, wt in qubo]
        return soln, na, objs

    def __setitem__(self, key, value):
        col_info, num_true = key
        sorted_info = sorted(col_info, key=lambda k: (k[1], k[0]))
        vars2vs = {var[0]: 'v%d' % i for i, var in enumerate(sorted_info)}
        key1 = json.dumps(sorted([(vars2vs[var], cnt)
                                  for var, cnt in col_info]))
        key2 = json.dumps(sorted(num_true))
        soln, na, objs = value
        qubo = [(vars2vs.setdefault(v1, v1),
                 vars2vs.setdefault(v2, v2),
                 wt)
                for v1, v2, wt in soln]
        try:
            # On-disk database
            self._sql_cur.execute('INSERT OR IGNORE INTO qubo_cache'
                                  ' VALUES (?, ?, ?, ?, ?)',
                                  (key1, key2,
                                   json.dumps(qubo), na, json.dumps(objs)))
            self._sql_con.commit()
        except AttributeError:
            # In-memory database
            self._qubo_cache[(key1, key2)] = json.dumps((qubo, na, objs))


class BQMMixin():
    'Mixin for an nchoosek.Constraint that converts the Constraint to a BQM'

    _qubo_cache = QUBOCache()  # Memoization of previous QUBO computations

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
        all_valids = []        # Each row's validity

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
            # As a heuristic, shuffle all possible ancilla columns.
            shuffled_anc = list(itertools.product(*[[0, 1]]*na))
            random.shuffle(shuffled_anc)

            # Construct a Z3 expression for each combination of ancillae for
            # this row.
            exprs = []
            for anc in shuffled_anc:
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
            all_valids.append(valid)
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

    def _compute_objectives(self, soln, na):
        'Compute the objective function for each row of the truth table.'
        # Consider in turn all 2**n possible variable assignments.
        objs = set()   # Unique objective values
        all_ports = self.port_list + ['_anc%d' % (i + 1)
                                      for i in range(na)]
        nbits = len(all_ports)
        for bits in range(2**nbits):
            # Compute the objective value of the current variable assignment.
            vals = {all_ports[i]: (bits >> i) & 1 for i in range(nbits)}
            o = 0
            for v0, v1, wt in soln:
                o += vals[v0]*vals[v1]*wt
            objs.add(o)
        return sorted(objs)

    def solve_qubo(self):
        '''Try increasing numbers of ancillae until the truth table can be
        expressed in terms of a QUBO's linear and quadratic coefficients.
        Return the solution (or None), the number of ancillae required, and
        a sorted list of unique objective values.'''
        tt, col_info = self._truth_table()
        try:
            # We already processed a similar constraint.
            soln, na, objs = self._qubo_cache[(col_info, self.num_true)]
            return soln, na, objs
        except KeyError:
            # We've not yet seen a similar constraint.
            nc = len(col_info)
            for na in range(0, nc):
                soln = self._solve_ancillae(tt, col_info, na)
                if soln is not None:
                    objs = self._compute_objectives(soln, na)
                    self._qubo_cache[(col_info, self.num_true)] = \
                        (soln, na, objs)
                    return soln, na, objs
            return None, na, set()  # Control should never reach this point.
