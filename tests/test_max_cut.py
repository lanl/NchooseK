import pytest

import nchoosek


@pytest.fixture()
def max_cut_env():
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
    env = nchoosek.Environment()
    a = env.register_port("A")
    b = env.register_port("B")
    c = env.register_port("C")
    d = env.register_port("D")
    e = env.register_port("E")
    for edges in [(a, b), (a, c), (b, c), (b, d), (c, e), (d, e)]:
        env.different(edges[0], edges[1], soft=True)

    solutions = [
        [["A", "B", "E"], ["C", "D"]],
        [["A", "C", "D"], ["B", "E"]],
        [["B", "E"], ["A", "C", "D"]],
        [["C", "D"], ["A", "B", "E"]],
    ]
    return env, solutions


@pytest.mark.parametrize("solver,", ["z3", "qiskit", "ocean"])
def test_max_cut(
    solver,
    max_cut_env,
):
    env, expected_solutions = max_cut_env[0], max_cut_env[1]
    result = env.solve(solver=solver)
    for soln in result.solutions:
        # any solution returned by solver should be correct.
        # note, not all solvers return multiple results.
        set1 = sorted([k for k, v in soln.items() if v])
        set2 = sorted([k for k, v in soln.items() if not v])

        assert [set1, set2] in expected_solutions


if __name__ == "__main__":
    pytest.main(["-v", __file__])
