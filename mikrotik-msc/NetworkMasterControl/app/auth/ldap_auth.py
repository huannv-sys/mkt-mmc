# File: app/auth/ldap_auth.py
import ldap

def authenticate_ldap(username, password):
    conn = ldap.initialize('ldap://ldap.example.com')
    try:
        conn.simple_bind_s(f"cn={username},ou=users,dc=example,dc=com", password)
        return True
    except ldap.INVALID_CREDENTIALS:
        return False
