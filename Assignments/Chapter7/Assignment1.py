def add_contact(contacts):
    """Add a new contact"""
    name = input("Enter name: ").strip()
    phone = input("Enter phone: ").strip()

    if not name:
        print("Error: Name cannot be empty.")
        return

    if not phone:
        print("Error: Phone cannot be empty.")
        return

    email = input("Enter email: ").strip()

    contact = {
        "name": name,
        "phone": phone,
        "email": email
    }

    contacts.append(contact)
    print("Contact added successfully!\n")


def list_contacts(contacts):
    """Display all contacts"""
    if not contacts:
        print("No contacts found.\n")
        return

    print("\n--- Contact List ---")
    for index, contact in enumerate(contacts, start=1):
        print(f"{index}. Name : {contact['name']}")
        print(f"   Phone: {contact['phone']}")
        print(f"   Email: {contact['email']}")
        print()
        

def search_contact(contacts):
    """Search contact by name"""
    search_name = input("Enter name to search: ").strip().lower()

    found = False

    for contact in contacts:
        if contact["name"].lower() == search_name:
            print("\nContact Found:")
            print(f"Name : {contact['name']}")
            print(f"Phone: {contact['phone']}")
            print(f"Email: {contact['email']}\n")
            found = True

    if not found:
        print("Contact not found.\n")


def main():
    contacts = []

    while True:
        print("===== Contact Book =====")
        print("1. Add Contact")
        print("2. List Contacts")
        print("3. Search Contact")
        print("4. Quit")

        choice = input("Enter your choice: ")

        if choice == "1":
            add_contact(contacts)

        elif choice == "2":
            list_contacts(contacts)

        elif choice == "3":
            search_contact(contacts)

        elif choice == "4":
            print("Goodbye!")
            break

        else:
            print("Invalid choice. Please try again.\n")


main()
