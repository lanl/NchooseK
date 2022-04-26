#! /usr/bin/env python

###################################
# Test NchooseK on a two-region   #
# map-coloring problem            #
#                                 #
# By Scott Pakin <pakin@lanl.gov> #
###################################

import nchoosek

# Define a type for "exactly one color".
env = nchoosek.Environment()
OneColor = env.new_type('one_color', 'RGBY',
                        nchoosek.Constraint('RGBY', {1}))
NotBothTrue = env.new_type('not_both_true', 'AB',
                           nchoosek.Constraint('AB', {0, 1}))

# Define all colors in all regions.
qld = [env.register_port('qld.' + c) for c in 'RGBY']
nsw = [env.register_port('nsw.' + c) for c in 'RGBY']

# Establish constraints.
qld_color = OneColor(qld)
nsw_color = OneColor(nsw)
for i in range(len(qld)):
    NotBothTrue([qld[i], nsw[i]])

# Output the environment.
print('Ports:')
print('    ', env.ports())
print('')
print('Constraints:')
for c in set(env.constraints()):
    print('    ', c)
print('')

# Solve for all variables in the environment.
result = env.solve()
soln = result.solutions[0]
for k, v in sorted(soln.items()):
    print('%-16s  %s' % (k, v))
