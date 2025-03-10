from enum import Enum

class Role(Enum):
    ADMIN = "admin"
    USER = "user"

class RBAC:
    def __init__(self):
        self.roles = {
            Role.ADMIN: ["create", "read", "update", "delete"],
            Role.USER: ["read"]
        }

    def has_permission(self, role, action):
        return action in self.roles.get(role, [])

# Example usage
if __name__ == "__main__":
    rbac = RBAC()
    print(rbac.has_permission(Role.ADMIN, "create"))
    print(rbac.has_permission(Role.USER, "delete"))
