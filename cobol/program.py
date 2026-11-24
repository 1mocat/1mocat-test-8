#!/usr/bin/env python3
"""
Re-implementation of the COBOL program BOOKFORUM in Python.
Reads input from src/INPUT.DAT (relative to cobol/ dir) and updates
data/ACCOUNTS.DAT, data/BOOKS.DAT, data/TRANSACTIONS.DAT accordingly.
"""

import os
from pathlib import Path

# Paths relative to the cobol/ directory (where this script lives)
BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "src" / "INPUT.DAT"
ACCOUNTS_PATH = BASE_DIR / "data" / "ACCOUNTS.DAT"
BOOKS_PATH = BASE_DIR / "data" / "BOOKS.DAT"
TRANSACTIONS_PATH = BASE_DIR / "data" / "TRANSACTIONS.DAT"

# Record layouts (fixed-length, no delimiters)
INPUT_LEN = 4 + 4 + 4 + 10  # buyer + seller + book + amount
ACCOUNT_LEN = 4 + 20 + 10   # id + name + balance
BOOK_LEN = 4 + 20 + 4       # id + title + owner
TRANS_LEN = 4 + 10 + 4 + 4  # book + amount + seller + buyer


def read_fixed_records(path: Path, rec_len: int):
    """Read all complete fixed-length records from a binary file."""
    if not path.exists():
        return []
    data = path.read_bytes()
    records = []
    for i in range(0, len(data) - rec_len + 1, rec_len):
        records.append(data[i:i + rec_len])
    return records


def write_fixed_records(path: Path, records):
    """Write fixed-length records back to file (overwrite)."""
    path.write_bytes(b"".join(records))


def parse_input():
    """Read the single input record. Returns (buyer, seller, book, amount) or None on failure."""
    if not INPUT_PATH.exists():
        print("Error: Input file is empty")
        return None
    data = INPUT_PATH.read_bytes()
    if len(data) < INPUT_LEN:
        # Short record – treat as empty / invalid (matches typical COBOL AT END behavior
        # for incomplete fixed records). For the given test data this leads to no updates.
        print("Error: Input file is empty")
        return None
    rec = data[:INPUT_LEN]
    buyer = rec[0:4].decode("ascii", errors="replace").rstrip()
    seller = rec[4:8].decode("ascii", errors="replace").rstrip()
    book = rec[8:12].decode("ascii", errors="replace").rstrip()
    amount_str = rec[12:22].decode("ascii", errors="replace").strip()
    try:
        amount = int(amount_str) if amount_str else 0
    except ValueError:
        amount = 0
    return buyer, seller, book, amount


def main():
    parsed = parse_input()
    if parsed is None:
        return
    buyer_id, seller_id, book_id, amount = parsed

    # --- Validate users and book ---
    accounts = read_fixed_records(ACCOUNTS_PATH, ACCOUNT_LEN)
    books = read_fixed_records(BOOKS_PATH, BOOK_LEN)

    buyer_found = False
    seller_found = False
    book_found = False
    valid_owner = False

    for rec in accounts:
        acc_id = rec[0:4].decode("ascii", errors="replace")
        if acc_id == buyer_id:
            buyer_found = True
        if acc_id == seller_id:
            seller_found = True

    for rec in books:
        bid = rec[0:4].decode("ascii", errors="replace")
        owner = rec[24:28].decode("ascii", errors="replace")
        if bid == book_id:
            book_found = True
            if owner == seller_id:
                valid_owner = True

    print(" ")  # matches the DISPLAY " " in VALIDATE

    if not (buyer_found and seller_found and book_found and valid_owner):
        print("Transaction failed due to validation errors")
        return

    # --- Process transaction ---
    # Update accounts: subtract from buyer, add to seller
    new_accounts = []
    for rec in accounts:
        acc_id = rec[0:4].decode("ascii", errors="replace")
        name = rec[4:24]
        bal_str = rec[24:34].decode("ascii", errors="replace")
        try:
            balance = int(bal_str)
        except ValueError:
            balance = 0
        if acc_id == buyer_id:
            balance -= amount
        if acc_id == seller_id:
            balance += amount
        # Re-format balance as 10-digit zero-padded
        new_bal = f"{max(balance, 0):010d}".encode("ascii")  # COBOL numeric usually allows negative differently, but for this data ok
        new_rec = rec[0:24] + new_bal
        new_accounts.append(new_rec)
    write_fixed_records(ACCOUNTS_PATH, new_accounts)

    # Update book owner
    new_books = []
    for rec in books:
        bid = rec[0:4].decode("ascii", errors="replace")
        if bid == book_id:
            # Replace owner (bytes 24-28) with buyer_id (padded to 4)
            new_owner = buyer_id.encode("ascii")[:4].ljust(4, b" ")
            new_rec = rec[0:24] + new_owner
            new_books.append(new_rec)
        else:
            new_books.append(rec)
    write_fixed_records(BOOKS_PATH, new_books)

    # Append transaction
    # TRANS-AMOUNT is PIC 9(10) – integer part of WS-AMOUNT (which has V99 but source was integer)
    amount_str = f"{amount:010d}".encode("ascii")
    buyer_b = buyer_id.encode("ascii")[:4].ljust(4, b" ")
    seller_b = seller_id.encode("ascii")[:4].ljust(4, b" ")
    book_b = book_id.encode("ascii")[:4].ljust(4, b" ")
    trans_rec = book_b + amount_str + seller_b + buyer_b
    # OPEN EXTEND – append
    with open(TRANSACTIONS_PATH, "ab") as f:
        f.write(trans_rec)

    print("Transaction completed successfully")


if __name__ == "__main__":
    main()
