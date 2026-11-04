import random

def number_guessing_game():
    target_number = random.randint(1, 100)
    attempts = 0

    print("Welcome to the Number Guessing Game!")
    print("I'm thinking of a number between 1 and 100.")

    while True:
        try:
            guess = int(input("Enter your guess: "))
            attempts += 1

            if guess < target_number:
                print("Too low! Try again.")

            elif guess > target_number:
                print("Too high! Try again.")

            else:
                print(f"Congratulations! You guessed the number {target_number}.")
                print(f"It took you {attempts} attempts.")
                break

        except ValueError:
            print("Invalid input! Please enter a valid number.")

number_guessing_game()
