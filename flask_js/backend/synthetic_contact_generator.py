import requests
import random
import faker

# Configuration
API_URL = "http://localhost:5000/create_contact"  # Adjust URL if deployed
BATCH_SIZE = 1000  # Number of contacts to create
faker_instance = faker.Faker()

def generate_contact():
    """Generate a synthetic contact."""
    return {
        "firstName": faker_instance.first_name(),
        "lastName": faker_instance.last_name(),
        "email": faker_instance.email(),
    }

def populate_database(batch_size):
    """Send PUT requests to create synthetic contacts."""
    for i in range(batch_size):
        contact_data = generate_contact()
        response = requests.post(API_URL, json=contact_data)
        
        if response.status_code == 200:
            print(f"Contact {i + 1}/{batch_size} created successfully.")
        else:
            print(f"Failed to create contact {i + 1}/{batch_size}: {response.text}")

if __name__ == "__main__":
    print(f"Starting to populate the database with {BATCH_SIZE} synthetic contacts...")
    populate_database(BATCH_SIZE)
    print("Database population complete!")
