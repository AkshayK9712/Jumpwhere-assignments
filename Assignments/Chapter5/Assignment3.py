from abc import ABC, abstractmethod


class InvalidAmountError(Exception):
    """Raised when a payment amount is zero or negative."""
    pass


class Payment(ABC):
    """
    Abstract base class representing a payment.
    Stores and validates the payment amount.
    """

    def __init__(self, amount):
        if amount <= 0:
            raise InvalidAmountError(
                f"Invalid amount: {amount}. Amount must be greater than zero."
            )

        self._amount = amount  # Protected attribute

    @property
    def amount(self):
        """Read-only access to the payment amount."""
        return self._amount

    @abstractmethod
    def pay(self):
        """Process the payment."""
        pass


class CreditCardPayment(Payment):
    """Payment processed using a credit card."""

    def pay(self):
        print(f"Credit Card payment of ${self.amount:.2f} processed.")


class UPIPayment(Payment):
    """Payment processed using UPI."""

    def pay(self):
        print(f"UPI payment of ${self.amount:.2f} processed.")


class WalletPayment(Payment):
    """Payment processed using a digital wallet."""

    def pay(self):
        print(f"Wallet payment of ${self.amount:.2f} processed.")


def process_payments(payments):
    """
    Process a collection of Payment objects.

    Demonstrates polymorphism by calling pay()
    on each object without knowing its exact type.
    """
    for payment in payments:
        payment.pay()


# -----------------------------------
# Demo
# -----------------------------------

payments = [
    CreditCardPayment(150.50),
    UPIPayment(299.99),
    WalletPayment(75.00)
]

print("Processing Payments:")
process_payments(payments)

print("\nAccessing amount via property:")
print(payments[0].amount)

print("\nTesting custom exception:")
try:
    invalid_payment = CreditCardPayment(-100)
except InvalidAmountError as e:
    print("Error:", e)
