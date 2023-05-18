import qiskit

def circuit_gen(env, quantum_instance=None):
    # Cost function and single circuit

    ports = env.ports()
    qubo = construct_qubo(env, None)
    # dictionary to hold the ising conversion of the qubo
    isin = {}
    # dictionary to be able to retrieve port numbers
    vardict = {}
    for idx, port in enumerate(ports):
        vardict[port] = idx
    for con in qubo:
        # Add ancillary bits to vardict
        if '_anc' in con[0] or '_anc' in con[1]:
            for c in con:
                # Surely there's a better way to add ancilla bits to vardict, without having to check each constraint...
                if c not in vardict:
                    idx += 1
                    vardict[c] = idx
        # Convert the QUBO to ising
        if con[0] == con[1]:
            if con in isin:
                isin[con] += qubo[con]/2
            else:
                isin[con] = qubo[con]/2
        else:
            three = [con, (con[0], con[0]), (con[1], con[1])]
            for c in three:
                if c in isin:
                    isin[c] += qubo[con]/4
                else:
                    isin[c] = qubo[con]/4

    siz = idx + 1
    # Coefficient matrix for calculating cost function
    # This matrix still uses the qubo variables: qiskit naturally returns 0 and 1
    mat = np.zeros((siz, siz))
    for con in qubo:
        mat[vardict[con[0]]][vardict[con[1]]] = qubo[con]
    # Quantum Circuit for QAOA
    qc = qiskit.QuantumCircuit(siz, siz)
    # Parameters to be optimized
    alpha = qiskit.circuit.Parameter('a')
    beta = qiskit.circuit.Parameter('b')

    # Initial state
    qc.h(range(siz))

    # Phase separator uses ising values 
    for con in isin:
        if isin[con] == 0.0:
            continue
        a = vardict[con[0]]
        b = vardict[con[1]]
        if a == b:
            qc.rz(-alpha*isin[con], a)
        else:
            qc.rzz(alpha*isin[con], a, b)

    # Universal mixer and measurement
    qc.rx(beta, range(siz))
    for p in range(siz):
        qc.measure(p, p)
    
    # If there's a quantum_instance given, transpile down to available basis gates
    if quantum_instance:
        qc = qiskit.transpile(qc, backend=quantum_instance.backend, basis_gates=quantum_instance.backend_config["basis_gates"], optimization_level=0)
    
    # Standard cost function; takes counts from qiskit running a circuit.
    # This evaluates every result returned and weights them by the coefficients.
    # For few qubits, this is essentially brute force.
    def ret(counts):
        totval = 0
        total = 0
        for count in counts:
            arr = np.array([int(x) for x in count], dtype=int)
            totval += counts[count]
            total += counts[count]*(arr.T @ mat @ arr)
        return total/totval

    return qc, ret
