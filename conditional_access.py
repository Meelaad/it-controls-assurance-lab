import argparse

import graph

# admin roles that always need MFA
ADMIN_ROLES = [
    "62e90394-69f5-4237-9190-012177145e10",  # global administrator
    "e8611ab8-c189-46e8-94e1-60213ab1f814",  # privileged role administrator
    "194ae4cb-b126-40b2-bd5b-6091b380977d",  # security administrator
    "fe930be7-5e62-47db-91af-98c3a49a38b1",  # user administrator
    "729827e3-9c14-49f7-bb1b-9608f156bbb8",  # helpdesk administrator
    "b1be1c3e-b65d-4f19-8427-f6fa0d97feb9",  # conditional access administrator
    "c4e39bd9-1100-46d3-8c65-fb160da0071f",  # authentication administrator
    "9b895d92-2cd3-44c7-9d02-a6ac2d5ea5c3",  # application administrator
]

# Replaces security defaults (they have to be off before CA policies can be turned on).
# labadmin isn't excluded, it already has MFA
POLICIES = [
    {
        "displayName": "CA01 Require MFA for admin roles",
        "conditions": {"users": {"includeRoles": ADMIN_ROLES},
                       "applications": {"includeApplications": ["All"]},
                       "clientAppTypes": ["all"]},
        "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
    },
    {
        "displayName": "CA02 Require MFA for all users",
        "conditions": {"users": {"includeUsers": ["All"]},
                       "applications": {"includeApplications": ["All"]},
                       "clientAppTypes": ["all"]},
        "grantControls": {"operator": "OR", "builtInControls": ["mfa"]},
    },
    {
        # legacy protocols can't do MFA
        "displayName": "CA03 Block legacy authentication",
        "conditions": {"users": {"includeUsers": ["All"]},
                       "applications": {"includeApplications": ["All"]},
                       "clientAppTypes": ["exchangeActiveSync", "other"]},
        "grantControls": {"operator": "OR", "builtInControls": ["block"]},
    },
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="create the policies, otherwise just print them")
    args = p.parse_args()

    existing = {x["displayName"] for x in graph.get_all("/identity/conditionalAccess/policies")}
    for policy in POLICIES:
        if policy["displayName"] in existing:
            print(policy["displayName"], "already exists")
            continue
        print("create", policy["displayName"])
        if args.apply:
            graph.post("/identity/conditionalAccess/policies", {**policy, "state": "enabled"})


if __name__ == "__main__":
    main()
