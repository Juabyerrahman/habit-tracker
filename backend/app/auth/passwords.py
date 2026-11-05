from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()  # Argon2id with library defaults
_DUMMY_HASH = _hasher.hash("timing-equalisation-only")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(stored_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(stored_hash: str) -> bool:
    return _hasher.check_needs_rehash(stored_hash)


def burn_time(password: str) -> None:
    """Hash-check against a dummy so 'unknown email' takes as long as 'wrong password'."""
    verify_password(_DUMMY_HASH, password)
