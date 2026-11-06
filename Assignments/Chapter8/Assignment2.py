class BankAccount:
    def __init__(self, initial_balance=0):
        self._validate_number(initial_balance)
        if initial_balance < 0:
            raise ValueError("Initial balance cannot be negative.")
        self.__balance = initial_balance

    @staticmethod
    def _validate_number(amount):
        # bool is a subclass of int, so exclude it explicitly
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Amount must be a number.")

    @property
    def balance(self):
        """Read-only access to the current balance."""
        return self.__balance

    def get_balance(self):
        return self.__balance

    def deposit(self, amount):
        self._validate_number(amount)
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self.__balance += amount

    def withdraw(self, amount):
        self._validate_number(amount)
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        if amount > self.__balance:
            raise ValueError("Insufficient funds.")
        self.__balance -= amount


if __name__ == "__main__":
    acct = BankAccount(100)
    acct.deposit(50)
    acct.withdraw(30)
    print(acct.balance)            # 120

    for action, amt in [(acct.deposit, -10), (acct.withdraw, 500)]:
        try:
            action(amt)
        except ValueError as e:
            print("Error:", e)

    try:
        acct.balance = 1_000_000   # no setter defined
    except AttributeError as e:
        print("Error:", e)

    acct.__balance = 1_000_000     # creates a separate, unrelated attribute
    print(acct.balance)            # still 120
