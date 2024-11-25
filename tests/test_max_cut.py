import pytest

import nchoosek


@pytest.mark.parametrize(
    "solver,",
    [("z3"), ("qiskit"), ("ocean")],
)
def test_max_cut(solver):
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
    result = env.solve(solver=solver)
    soln = result.solutions[0]

    set1 = sorted([k for k, v in soln.items() if v])
    set2 = sorted([k for k, v in soln.items() if not v])

    expected_set1 = [["A", "B", "E"], ["C", "D"]]
    expected_set2 = [["A", "C", "D"], ["B", "E"]]

    assert set1 in expected_set1 or set1 in expected_set2
    assert set2 in expected_set1 or set2 in expected_set2

    assert [set1, set2] == expected_set1 or [set1, set2] == expected_set2


if __name__ == "__main__":
    pytest.main(["-v", __file__])
