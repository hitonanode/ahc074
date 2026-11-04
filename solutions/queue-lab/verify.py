"""Exhaustively check the subsequence description of shortest extraction plans."""
from itertools import permutations

n=5
orders=list(permutations(range(n)))
checked=0
for order in orders:
    for depth in range(n):
        target=order[depth]
        frontier={order}
        for step in range(depth):
            next_states=set()
            for state in frontier:
                head,tail=state[0],list(state[1:])
                first=tail.index(target)+1
                for dest in range(first,n):
                    row=tail[:];row.insert(dest,head);next_states.add(tuple(row))
            frontier=next_states
        reached=set()
        for state in frontier:
            assert state[0]==target
            for dest in range(n):
                row=list(state[1:]);row.insert(dest,target);reached.add(tuple(row))
        suffix=order[depth+1:]
        predicted=set()
        for state in orders:
            it=iter(state)
            if all(any(x==wanted for x in it) for wanted in suffix):predicted.add(state)
        assert reached==predicted
        checked+=1
print(f"shortest extraction and arbitrary return: {checked} states/targets checked")
