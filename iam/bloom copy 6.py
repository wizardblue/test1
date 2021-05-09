def get_all_entities_for_policy(policy_arn):
    iam_client = boto3.client("iam")

    marker = 'marker'
    policy_groups = []
    policy_users = []
    policy_roles = []
    while marker:
        params = remove_none_attributes({
            "PolicyArn": policy_arn,
            "MaxItems": 100,
            "Marker": marker if marker != "marker" else None
        })

        response = iam_client.list_entities_for_policy(**params)

        policy_groups.extend(response.get("PolicyGroups", []))
        policy_users.extend(response.get("PolicyUsers", []))
        policy_roles.extend(response.get("PolicyRoles", []))

        marker = response.get("Marker")

    return policy_groups, policy_users, policy_roles
