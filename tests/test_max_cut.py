import pytest

import nchoosek

NCSU_INSTANCE = "ibm-q-ncsu/nc-state/noise"


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


@pytest.mark.parametrize(
    "solver,backend,instance",
    [
        ("z3", None, None),
        ("qiskit", None, None),
        ("ocean", None, None),
        # actually uses hardware
        # ("qiskit", "ibm_strasbourg", NCSU_INSTANCE),
    ],
)
def test_max_cut(
    solver,
    backend,
    instance,
    max_cut_env,
):
    env, expected_solutions = max_cut_env[0], max_cut_env[1]
    result = env.solve(solver=solver, backend=backend, instance=instance)
    for energy, soln in zip(result.energies, result.solutions):
        # any solution returned by solver should be correct.
        # note, not all solvers return multiple results.
        if energy == -5:
            set1 = sorted([k for k, v in soln.items() if v])
            set2 = sorted([k for k, v in soln.items() if not v])

            assert [set1, set2] in expected_solutions


if __name__ == "__main__":
    pytest.main(["-v", __file__])
