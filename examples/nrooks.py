#! /usr/bin/env python

###################################
# Solve the n-rooks problem       #
# with NchooseK                   #
#                                 #
# By Scott Pakin <pakin@lanl.gov> #
###################################

import nchoosek
import sys

# Read the number of rooks from the command line.
if len(sys.argv) < 2:
    sys.exit('Usage: %s <#rooks>' % sys.argv[0])
n = int(sys.argv[1])

# Define an nxn chessboard.
env = nchoosek.Environment()
idxs = range(1, n + 1)
board = [[env.register_port('A[%d][%d]' % (r, c)) for r in idxs] for c in idxs]

# Ensure that exactly one rook lies in each row and in each column.
ExactlyOne = env.new_type('one', idxs, nchoosek.Constraint(idxs, {1}))
for r in idxs:
    ExactlyOne([board[r - 1][c - 1] for c in idxs])
for c in idxs:
    ExactlyOne([board[r - 1][c - 1] for r in idxs])

# Solve for all variables in the environment.
result = env.solve()
for r in idxs:
    for c in idxs:
        if result['A[%d][%d]' % (r, c)]:
            print('* ', end='')
        else:
            print('- ', end='')
    print('')
