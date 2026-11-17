import argparse
import csv
import os

import graph

# signInActivity and the MFA registration report need P1/P2, otherwise those columns are n/a


def write_csv(path, rows, fields):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="evidence")
    args = p.parse_args()
    os.makedirs(args.out, exist_ok=True)

    users = graph.get_all("/users?$select=id,userPrincipalName,displayName,department,jobTitle,accountEnabled")
    by_id = {u["id"]: u for u in users}

    last_sign_in = {}
    if graph.get("/users?$select=id,signInActivity&$top=1") is not None:
        for u in graph.get_all("/users?$select=id,signInActivity"):
            last_sign_in[u["id"]] = ((u.get("signInActivity") or {}).get("lastSignInDateTime") or "never")[:10]
    mfa = {}
    if graph.get("/reports/authenticationMethods/userRegistrationDetails?$top=1") is not None:
        for r in graph.get_all("/reports/authenticationMethods/userRegistrationDetails"):
            mfa[r["id"]] = "yes" if r["isMfaRegistered"] else "no"

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
            "mfa_registered": mfa.get(u["id"], "n/a"),
            "last_sign_in": last_sign_in.get(u["id"], "n/a"),
            "groups": "|".join(sorted(groups_of[u["id"]])),
            "roles": "|".join(sorted(roles_of[u["id"]])),
        })

    write_csv(os.path.join(args.out, "entra_users.csv"), user_rows, list(user_rows[0]))
    write_csv(os.path.join(args.out, "entra_roles.csv"),
              sorted(role_rows, key=lambda r: (r["role"], r["user"])), ["user", "role", "scope"])
    print(f"{len(user_rows)} users, {len(role_rows)} role assignments")


if __name__ == "__main__":
    main()
