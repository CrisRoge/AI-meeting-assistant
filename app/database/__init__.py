# Expose database initialization and core query functions
from .db_setup import initialize_db

# We will add imports from queries.py here later
# e.g., from .queries import create_meeting, get_all_meetings

__all__ = ["initialize_db"]