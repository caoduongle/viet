"""Điểm vào thực thi khi gọi `python -m chuviettay`."""
import sys
from chuviettay.cli import main

if __name__ == "__main__":
    sys.exit(main())
