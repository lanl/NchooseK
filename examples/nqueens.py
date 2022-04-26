#! /usr/bin/env python

###################################
# Solve the n-queens problem      #
# with NchooseK                   #
#                                 #
# By Scott Pakin <pakin@lanl.gov> #
###################################

import nchoosek
import sys

# Read the number of queens from the command line.
if len(sys.argv) < 2:
    sys.exit('Usage: %s <#queens>' % sys.argv[0])
n = int(sys.argv[1])

# Define an nxn chessboard.
env = nchoosek.Environment()
idxs = range(1, n + 1)
board = [[env.register_port('A[%d][%d]' % (r, c)) for r in idxs] for c in idxs]

# Ensure that exactly one queen lies in each row and in each column.
ExactlyOne = env.new_type('one', idxs, nchoosek.Constraint(idxs, {1}))
for r in idxs:
    ExactlyOne([board[r - 1][c - 1] for c in idxs])
for c in idxs:
    ExactlyOne([board[r - 1][c - 1] for r in idxs])

# Construct a list of all diagonals.
all_diags = []
for r in idxs[:-1]:
    # Below and equal to the main diagonal
    diag = []
    for ofs in range(n):
        if r + ofs <= n:
            diag.append('A[%d][%d]' % (r + ofs, 1 + ofs))
    all_diags.append(diag)

    # Below and equal to the main antidiagonal
    diag = []
    for ofs in range(n):
        if r + ofs <= n:
            diag.append('A[%d][%d]' % (r + ofs, n - ofs))
    all_diags.append(diag)
for c in idxs[1:-1]:
    # Above the main diagonal
    diag = []
    for ofs in range(n):
        if c + ofs <= n:
            diag.append('A[%d][%d]' % (1 + ofs, c + ofs))
    all_diags.append(diag)

    # Above the main antidiagonal
    diag = []
    for ofs in range(n):
        r = n - ofs - c + 1
        if r >= 1:
            diag.append('A[%d][%d]' % (r, 1 + ofs))
    all_diags.append(diag)

# Limit diagonals to either zero or one queen.
for diag in all_diags:
    env.nck(diag, {0, 1})

# Solve for all variables in the environment.
result = env.solve()
soln = result.solutions[0]
for r in idxs:
    for c in idxs:
        if soln['A[%d][%d]' % (r, c)]:
            print('* ', end='')
        else:
            print('- ', end='')
    print('')
