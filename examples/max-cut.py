#! /usr/bin/env python

#######################################
# Solve the following max-cut problem #
# with NchooseK:                      #
#                                     #
#       A                             #
#      / \                            #
#     B - C                           #
#     |   |                           #
#     D - E                           #
#                                     #
# By Scott Pakin <pakin@lanl.gov>     #
#######################################

import nchoosek

env = nchoosek.Environment()
a = env.register_port('A')
b = env.register_port('B')
c = env.register_port('C')
d = env.register_port('D')
e = env.register_port('E')
for edges in [(a, b),
              (a, c),
              (b, c),
              (b, d),
              (c, e),
              (d, e)]:
    env.different(edges[0], edges[1], soft=True)
result = env.solve()
print('Partition 1: %s' %
      ' '.join(sorted([k for k, v in result.items() if v])))
print('Partition 2: %s' %
      ' '.join(sorted([k for k, v in result.items() if not v])))
