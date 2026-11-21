import os
import mysql.connector


def get_connection():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        database=os.environ.get("DB_NAME")
    )


def add_contact(name, email, phone):
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        INSERT INTO contacts (name, email, phone)
        VALUES (%s, %s, %s)
        """
        cursor.execute(query, (name, email, phone))

        conn.commit()
        print("Contact added successfully.")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error adding contact: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def list_contacts():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, name, email, phone FROM contacts"
        )

        contacts = cursor.fetchall()

        print("\nContacts:")
        for contact in contacts:
            print(contact)

    except Exception as e:
        print(f"Error listing contacts: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def update_contact(contact_id, name, email, phone):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        UPDATE contacts
        SET name=%s, email=%s, phone=%s
        WHERE id=%s
        """

        cursor.execute(
            query,
            (name, email, phone, contact_id)
        )

        conn.commit()
        print("Contact updated successfully.")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error updating contact: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def delete_contact(contact_id):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = "DELETE FROM contacts WHERE id=%s"

        cursor.execute(query, (contact_id,))

        conn.commit()
        print("Contact deleted successfully.")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error deleting contact: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def menu():
    while True:
        print("\n--- Contact Manager ---")
        print("1. Add Contact")
        print("2. List Contacts")
        print("3. Update Contact")
        print("4. Delete Contact")
        print("5. Exit")

        choice = input("Enter choice: ")

        if choice == "1":
            name = input("Name: ")
            email = input("Email: ")
            phone = input("Phone: ")
            add_contact(name, email, phone)

        elif choice == "2":
            list_contacts()

        elif choice == "3":
            contact_id = int(input("Contact ID: "))
            name = input("New Name: ")
            email = input("New Email: ")
            phone = input("New Phone: ")

            update_contact(
                contact_id,
                name,
                email,
                phone
            )

        elif choice == "4":
            contact_id = int(input("Contact ID: "))
            delete_contact(contact_id)

        elif choice == "5":
            print("Goodbye!")
            break

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    menu()
