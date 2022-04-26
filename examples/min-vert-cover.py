#! /usr/bin/env python

######################################
# Solve the following minimum vertex #
# cover problem with NchooseK:       #
#                                    #
#   6 - 4 - 5 - 1                    #
#       |   |   |                    #
#       3 - 2 --+                    #
#                                    #
# By Scott Pakin <pakin@lanl.gov>    #
######################################

import nchoosek

env = nchoosek.Environment()
verts = [env.register_port(str(i + 1)) for i in range(6)]
for u, v in [(1, 2),
             (1, 5),
             (2, 3),
             (2, 5),
             (3, 4),
             (4, 6)]:
    env.nck([verts[u - 1], verts[v - 1]], {1, 2})
env.minimize(verts)
result = env.solve()
soln = result.solutions[0]
print('Minimum vertex cover: %s' %
      ' '.join(sorted([v for v, b in soln.items() if b], key=int)))
