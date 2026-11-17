import argparse
import os

import graph

DOMAIN = os.environ.get("LAB_DOMAIN")
USER_ADMIN = "fe930be7-5e62-47db-91af-98c3a49a38b1"
HELPDESK_ADMIN = "729827e3-9c14-49f7-bb1b-9608f156bbb8"

# F-01 and F-02. F-03 is a process change, nothing to do in the tenant for it


def user(alias):
    u = graph.get(f"/users/{alias}@{DOMAIN}?$select=id,accountEnabled")
    if not u:
        raise SystemExit(f"{alias} not found")
    return u


def assignments(user_id, role_id):
    return graph.get_all(f"/roleManagement/directory/roleAssignments"
                         f"?$filter=principalId eq '{user_id}' and roleDefinitionId eq '{role_id}'")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="make the changes, otherwise just print them")
    args = p.parse_args()
    if not DOMAIN:
        raise SystemExit("set LAB_DOMAIN to the tenant's onmicrosoft.com domain first")

    # F-01: leaver still enabled
    rpatel = user("rpatel")
    if rpatel["accountEnabled"]:
        print("disable rpatel (left 2026-09-30, HR-1057)")
        if args.apply:
            graph.patch(f"/users/{rpatel['id']}", {"accountEnabled": False})

    # F-02: disabled, not deleted, so the audit logs still resolve to it
    temp = user("tempadmin")
    if temp["accountEnabled"]:
        print("disable tempadmin")
        if args.apply:
            graph.patch(f"/users/{temp['id']}", {"accountEnabled": False})
    for a in assignments(temp["id"], "62e90394-69f5-4237-9190-012177145e10"):
        print("remove Global Administrator from tempadmin")
        if args.apply:
            graph.call("delete", f"/roleManagement/directory/roleAssignments/{a['id']}")

    # F-02: jwalsh gets Helpdesk Admin as eligible in PIM instead, so no standing roles.
    # PIM was set up in the portal, the CLI token can't write it
    jwalsh = user("jwalsh")
    for role, name in ((USER_ADMIN, "User Administrator"), (HELPDESK_ADMIN, "Helpdesk Administrator")):
        for a in assignments(jwalsh["id"], role):
            print(f"remove standing {name} from jwalsh")
            if args.apply:
                graph.call("delete", f"/roleManagement/directory/roleAssignments/{a['id']}")


if __name__ == "__main__":
    main()
