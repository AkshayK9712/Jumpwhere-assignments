import random
import time

# Generate sample data
existing_orders = list(range(100000))

incoming_orders = [
    random.randint(0, 120000)
    for _ in range(10000)
]


# ----------------------
# Original Approach
# ----------------------
start = time.perf_counter()

matches_slow = []

for order_id in incoming_orders:
    if order_id in existing_orders:
        matches_slow.append(order_id)

slow_time = time.perf_counter() - start


# ----------------------
# Optimized Approach
# ----------------------
start = time.perf_counter()

existing_set = set(existing_orders)

matches_fast = []

for order_id in incoming_orders:
    if order_id in existing_set:
        matches_fast.append(order_id)

fast_time = time.perf_counter() - start


# ----------------------
# Results
# ----------------------
print(f"Slow version: {slow_time:.6f} seconds")
print(f"Fast version: {fast_time:.6f} seconds")
print(f"Speedup: {slow_time / fast_time:.2f}x")
print(f"Matches found: {len(matches_fast)}")
