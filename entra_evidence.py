import csv

import graph


def write_csv(name, rows, fields):
    with open(f"evidence/{name}", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    users = graph.get_all("/users?$select=id,userPrincipalName,displayName,department,jobTitle,accountEnabled")
    by_id = {u["id"]: u for u in users}

    groups_of = {u["id"]: [] for u in users}
    for g in graph.get_all("/groups?$select=id,displayName"):
        for m in graph.get_all(f"/groups/{g['id']}/members?$select=id"):
            if m["id"] in groups_of:
                groups_of[m["id"]].append(g["displayName"])

    role_names = {r["id"]: r["displayName"] for r in graph.get_all("/roleManagement/directory/roleDefinitions?$select=id,displayName")}
    roles_of = {u["id"]: [] for u in users}
    role_rows = []
    for a in graph.get_all("/roleManagement/directory/roleAssignments"):
        user = by_id.get(a["principalId"])
        if not user:
            continue  # service principals hold roles too, skip them
        name = role_names.get(a["roleDefinitionId"], a["roleDefinitionId"])
        roles_of[user["id"]].append(name)
        role_rows.append({"user": user["userPrincipalName"].split("@")[0], "role": name, "scope": a["directoryScopeId"]})

    user_rows = []
    for u in sorted(users, key=lambda u: u["userPrincipalName"]):
        user_rows.append({
            "user": u["userPrincipalName"].split("@")[0],
            "name": u["displayName"],
            "department": u.get("department") or "",
            "job_title": u.get("jobTitle") or "",
            "enabled": "yes" if u["accountEnabled"] else "no",
            "groups": "|".join(sorted(groups_of[u["id"]])),
            "roles": "|".join(sorted(roles_of[u["id"]])),
        })

    write_csv("entra_users.csv", user_rows, list(user_rows[0]))
    write_csv("entra_roles.csv", sorted(role_rows, key=lambda r: (r["role"], r["user"])), ["user", "role", "scope"])
    print(f"{len(user_rows)} users, {len(role_rows)} role assignments")


if __name__ == "__main__":
    main()
