import hashlib
def hash_data(data: str) -> str:
    return hashlib.sha256(data.strip().lower().encode()).hexdigest()

email = "test_donor1@example.com"
print(f"Original: {email}")
print(f"Hash: {hash_data(email)}")
