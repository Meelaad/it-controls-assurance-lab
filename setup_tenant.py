import os
import secrets

import graph

DOMAIN = os.environ.get("LAB_DOMAIN")

# built-in role template ids
GLOBAL_ADMIN = "62e90394-69f5-4237-9190-012177145e10"
USER_ADMIN = "fe930be7-5e62-47db-91af-98c3a49a38b1"

GROUPS = ["AP-Clerks", "AP-Managers", "Finance-Analysts", "IT-Support"]

# Northwind staff. A few control gaps are seeded on purpose:
# - rpatel left on 2026-09-30 (hr_leavers.csv) but is still enabled
# - jwalsh (IT support) kept User Administrator after a migration
# - tempadmin is a global admin set up "for later", never signed in so no MFA
# alias, display name, department, job title, group, roles, enabled
USERS = [
    ("akhan", "Aisha Khan", "Finance", "AP Clerk", "AP-Clerks", [], True),
    ("rpatel", "Ryan Patel", "Finance", "AP Clerk", "AP-Clerks", [], True),
    ("dmoreau", "Daniel Moreau", "Finance", "AP Manager", "AP-Managers", [], True),
    ("pshah", "Priya Shah", "Finance", "Financial Analyst", "Finance-Analysts", [], True),
    ("eclarke", "Emma Clarke", "Finance", "Financial Analyst", "Finance-Analysts", [], False),
    ("jwalsh", "Jordan Walsh", "IT", "IT Support Analyst", "IT-Support", [USER_ADMIN], True),
    ("tempadmin", "Temp Admin", "IT", "", None, [GLOBAL_ADMIN], True),
]


def find_group(name):
    found = graph.get(f"/groups?$filter=displayName eq '{name}'&$select=id")["value"]
    if found:
        return found[0]["id"]
    return graph.post("/groups", {
        "displayName": name, "mailNickname": name.lower(),
        "mailEnabled": False, "securityEnabled": True,
    })["id"]


def main():
    if not DOMAIN:
        raise SystemExit("set LAB_DOMAIN to the tenant's onmicrosoft.com domain first")

    groups = {name: find_group(name) for name in GROUPS}

    for alias, name, dept, title, group, roles, enabled in USERS:
        upn = f"{alias}@{DOMAIN}"
        user = graph.get(f"/users/{upn}?$select=id,accountEnabled")
        if user:
            print(alias, "already exists")
        else:
            body = {
                "accountEnabled": True, "displayName": name, "mailNickname": alias,
                "userPrincipalName": upn, "department": dept,
                "passwordProfile": {"password": secrets.token_urlsafe(24), "forceChangePasswordNextSignIn": True},
            }
            if title:
                body["jobTitle"] = title
            user = graph.post("/users", body)
            print(alias, "created")

        if group:
            members = graph.get_all(f"/groups/{groups[group]}/members?$select=id")
            if user["id"] not in {m["id"] for m in members}:
                graph.post(f"/groups/{groups[group]}/members/$ref",
                           {"@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{user['id']}"})
                print("  added to", group)

        assigned = {a["roleDefinitionId"] for a in graph.get_all(
            f"/roleManagement/directory/roleAssignments?$filter=principalId eq '{user['id']}'")}
        for role in roles:
            if role not in assigned:
                graph.post("/roleManagement/directory/roleAssignments",
                           {"principalId": user["id"], "roleDefinitionId": role, "directoryScopeId": "/"})
                print("  assigned role", role)

        if not enabled and user.get("accountEnabled", True):
            graph.patch(f"/users/{user['id']}", {"accountEnabled": False})
            print("  disabled")


if __name__ == "__main__":
    main()
