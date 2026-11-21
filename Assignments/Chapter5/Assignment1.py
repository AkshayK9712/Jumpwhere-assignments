from collections import deque


class EmptyCollectionError(Exception):
    """Raised when attempting to access an empty stack or queue."""
    pass


class Stack:
    def __init__(self):
        self._items = []

    # Time Complexity: O(1)
    def push(self, item):
        self._items.append(item)

    # Time Complexity: O(1)
    def pop(self):
        if self.is_empty():
            raise EmptyCollectionError("Cannot pop from an empty stack.")
        return self._items.pop()

    # Time Complexity: O(1)
    def peek(self):
        if self.is_empty():
            raise EmptyCollectionError("Cannot peek into an empty stack.")
        return self._items[-1]

    # Time Complexity: O(1)
    def is_empty(self):
        return len(self._items) == 0

    # Time Complexity: O(1)
    def size(self):
        return len(self._items)


class Queue:
    def __init__(self):
        self._items = deque()

    # Time Complexity: O(1)
    def enqueue(self, item):
        self._items.append(item)

    # Time Complexity: O(1)
    def dequeue(self):
        if self.is_empty():
            raise EmptyCollectionError("Cannot dequeue from an empty queue.")
        return self._items.popleft()

    # Time Complexity: O(1)
    def peek(self):
        if self.is_empty():
            raise EmptyCollectionError("Cannot peek into an empty queue.")
        return self._items[0]

    # Time Complexity: O(1)
    def is_empty(self):
        return len(self._items) == 0

    # Time Complexity: O(1)
    def size(self):
        return len(self._items)


def is_balanced(brackets):
    """
    Check if brackets are balanced using a Stack.
    Time Complexity: O(n)
    """
    stack = Stack()

    pairs = {
        ')': '(',
        ']': '[',
        '}': '{'
    }

    for ch in brackets:
        if ch in "([{":
            stack.push(ch)
        elif ch in ")]}":
            if stack.is_empty():
                return False

            if stack.pop() != pairsreturn False

    return stack.is_empty()


def process_jobs():
    """
    Simulate processing jobs in arrival order using a Queue.
    """
    queue = Queue()

    jobs = [
        "Job-1",
        "Job-2",
        "Job-3",
        "Job-4",
        "Job-5"
    ]

    for job in jobs:
        queue.enqueue(job)

    print("Processing jobs:")

    while not queue.is_empty():
        current_job = queue.dequeue()
        print(f"Processed {current_job}")


# -------------------------
# Demo
# -------------------------

print("=== Stack Demo ===")
test_string = "{[()]}"
print(f"Bracket string: {test_string}")
print("Balanced:", is_balanced(test_string))

print("\n=== Queue Demo ===")
process_jobs()

print("\n=== Exception Demo ===")
empty_stack = Stack()

try:
    empty_stack.pop()
except EmptyCollectionError as e:
    print("Stack Error:", e)

empty_queue = Queue()

try:
    empty_queue.peek()
except EmptyCollectionError as e:
    print("Queue Error:", e)
