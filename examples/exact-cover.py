#! /usr/bin/env python

########################################
# Solve the following exact cover      #
# problem with NchooseK:               #
#                                      #
# Given a set E = {a,b,c,d,e,f,g}      #
# and the following subsets of E       #
#                                      #
#   S1 = {b,c,e,f}                     #
#   S2 = {a,d,e}                       #
#   S3 = {a,d,e,g}                     #
#   S4 = {a,g,f}                       #
#   S5 = {c,f}                         #
#   S6 = {b,g}                         #
#                                      #
# find a subset of {S1,S2,S3,S4,S5,S6} #
# such that each element of E appears  #
# exactly once.                        #
#                                      #
# By Scott Pakin <pakin@lanl.gov>      #
########################################

import nchoosek

env = nchoosek.Environment()
S = [None] + [env.register_port('S%d' % i)
              for i in range(1, 7)]  # Number from 1.
env.nck([S[2], S[3], S[4]], {1})
env.nck([S[1], S[6]], {1})
env.nck([S[1], S[5]], {1})
env.nck([S[2], S[3]], {1})
env.nck([S[1], S[2], S[3]], {1})
env.nck([S[1], S[4], S[5]], {1})
env.nck([S[3], S[4], S[6]], {1})
result = env.solve()
soln = result.solutions[0]
print('Exact vertex cover: %s' %
      (' '.join(sorted([k for k, v in soln.items() if v]))))
