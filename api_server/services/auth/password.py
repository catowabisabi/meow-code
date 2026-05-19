from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


class PasswordService:
    def __init__(self):
        self.hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
        )

    def hash(self, password: str) -> str:
        return self.hasher.hash(password)

    def verify(self, hashed_password: str, password: str) -> bool:
        try:
            return self.hasher.verify(hashed_password, password)
        except VerifyMismatchError:
            return False

    def needs_rehash(self, hashed_password: str) -> bool:
        return self.hasher.check_needs_rehash(hashed_password)