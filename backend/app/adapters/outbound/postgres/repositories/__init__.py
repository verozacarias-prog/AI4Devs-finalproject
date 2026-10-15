"""The repositories: each one implements a `*_repository` port over one open connection.

They translate an entity to the parameters of a query and back, and nothing else. The SQL is
in `queries.py`.
"""
