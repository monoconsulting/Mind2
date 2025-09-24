import tracemalloc


def test_memory_growth_stable_small_loop():
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # allocate and release in a small loop
    for _ in range(1000):
        data = bytearray(1024)
        del data

    snapshot2 = tracemalloc.take_snapshot()
    # Compute total allocated size difference
    stats = snapshot2.compare_to(snapshot1, 'lineno')
    total_diff = sum(stat.size_diff for stat in stats)

    # We expect negligible diff; allow small slack (100KB)
    assert total_diff < 100 * 1024
