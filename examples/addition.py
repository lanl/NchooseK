#! /usr/bin/env python

################################################
# Demonstrate that NchooseK can be used to add #
# integers (although not particularly easily)  #
#                                              #
# By Scott Pakin <pakin@lanl.gov>              #
################################################

# This example also shows how to invoke a specific solver.

import argparse
import nchoosek
import sys

# Parse the command line.
parser = argparse.ArgumentParser(description='Add two numbers using NchooseK.')
parser.add_argument('augend', type=int, metavar='NUM1',
                    help='First number to add')
parser.add_argument('addend', type=int, metavar='NUM2',
                    help='Second number to add')
parser.add_argument('--bits', '-b', type=int, metavar='INT',
                    help='Number of bits to use for each input')
parser.add_argument('--solver', '-s', choices=['z3', 'ocean'], default='z3',
                    help='Solver to use to perform the addition')
parser.add_argument('--samples', type=int, metavar='INT', default=10,
                    help='Number of samples to take from the ocean solver')
cl_args = parser.parse_args()
num1 = cl_args.augend
num2 = cl_args.addend
if num1 < 0 or num2 < 0:
    sys.exit('%s: negative numbers are not yet supported' % sys.argv[0])
nbits = cl_args.bits
if nbits is None:
    nbits = 1
    mval = max(num1, num2) >> 1
    while mval > 0:
        nbits += 1
        mval >>= 1
if num1 >= 2**nbits:
    sys.exit('%s: the number %d cannot be represented with %d bit(s)' %
             (sys.argv[0], num1, nbits))
if num2 >= 2**nbits:
    sys.exit('%s: the number %d cannot be represented with %d bit(s)' %
             (sys.argv[0], num2, nbits))

# Create an environment.
env = nchoosek.Environment()

# Define a full adder.  The tt2nck helper program was used to construct this
# primitive.
Adder = env.new_type('adder',
                     ['carry-in', 'A', 'B', 'C1', 'C0'],
                     nchoosek.Constraint(['carry-in', 'A', 'B',
                                          *2*['C1'], *3*['C0']], {0, 4, 8}))

# Define one port per input bit, output bit, and carry bit.
a = [env.register_port('A%d' % i) for i in range(nbits)]
b = [env.register_port('B%d' % i) for i in range(nbits)]
c = [env.register_port('C%d' % i) for i in range(nbits + 1)]
cout = [env.register_port('cout%d' % i) for i in range(nbits)]

# Assign a value to each input bit.
for i in range(nbits):
    env.nck([a[i]], {(num1 >> i) & 1})
    env.nck([b[i]], {(num2 >> i) & 1})

# Define our carry-in to be initially False then the previous carry-out.
always_false = env.register_port('false')
env.nck([always_false], {0})
cin = [always_false] + cout  # Alias each input with the previous output.

# Add from right to left with carry.
for i in range(nbits):
    Adder([cin[i], a[i], b[i], cout[i], c[i]])
env.same(c[nbits], cout[nbits - 1])

# Solve for the sum.
if cl_args.solver == 'z3':
    from nchoosek.solver import z3
    soln = z3.solve(env)
elif cl_args.solver == 'ocean':
    from nchoosek.solver import ocean
    soln = ocean.solve(env, num_reads=cl_args.samples)
else:
    sys.exit('%s: Internal error -- unknown solver "%s"' %
             (sys.argv[0], cl_args.solver))

# Output the sum as an integer.
num3 = 0
for i in range(nbits, -1, -1):
    num3 <<= 1
    num3 += int(soln['C%d' % i])
print('%d + %d = %d' % (num1, num2, num3))
