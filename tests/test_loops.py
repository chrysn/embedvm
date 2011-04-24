from testsuite import userfunc as uf, end

def main():
    for i in range(5):
        if i == 3:
            continue
        uf(1, i)

    # with c style for, the last value for i is greater than the last value inside the loop; with python style range loops, it isn't
    i = i + 1

    # there are no do/while loops in python
    while True:
        uf(2, i)
        i = i - 1 # TBD: --
        if not i > 0:
            break

    k = i
    while i < 20:
        i = i + 1 # TBD: ++
        if i % 2 == 0:
            continue
        uf(3, i, k)
        k = k + 1 # TBD: ++

    # you just wouldn't do that in python...
    i = i + 1
    while i < 50:
        if i == 23:
            break
        uf(4, i)
        i = i + 1 # repeated from above

    # for(..;;..): no intent to implement this -- count can't do custom
    # increments
    # hackish solution using maxint
    for k in range(i-3, 32767):
        uf(5, k, i+k)
        if i + k == 50:
            break
        if (i + k) % 2 == 0:
            continue
        uf(6, i+k)

    for i in range(5):
        if i % 2 != 0:
            uf(7, True, i)
        else:
            uf(7, False, i)

if __name__ == "__main__":
    main()
    end()
