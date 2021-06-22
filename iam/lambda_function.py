import boto3
import botocore
import jsonschema
import json

from util import remove_none_attributes

def validate_state(state):

    jsonschema.validate()


def lambda_handler(event, context):
    if event.get("op") == "upsert":

        prev_state = event.get("prev_state")
        document = event.get("document")
        description = event.get("description") or "This policy was created by Wizard Blue for component"
        policy_name = event.get("name")
        path = event.get("path")

        if prev_state:
            try:
                validate_state(prev_state)
                prev_policy_arn = prev_state["props"]["policy_arn"]
                prev_policy_name = prev_state["props"]["policy_name"]
            except:
                prev_state = None
                prev_policy_arn = None
                prev_policy_name = None

        iam_client = boto3.client("iam")

        if prev_policy_arn:
            try:
                result = iam_client.get_policy(
                    PolicyArn = prev_policy_arn
                )
            except: #The policy doesn't exist
                prev_policy_arn = None

        create = not prev_policy_arn or (prev_policy_name != policy_name)
        delete_old_versions = not create
        remove_old = prev_policy_arn and (prev_policy_name != policy_name)

        #Create
        if create:

            try:
                result = iam_client.create_policy(remove_none_attributes({
                    "PolicyName": policy_name,
                    "Description": description,
                    "Path": path,
                    "PolicyDocument": json.dumps(document)
                }))

                policy_arn = result["Policy"]["Arn"]
            
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == 'EntityAlreadyExists':
                    delete_old_versions = True
                    arn = f"arn:aws:iam::aws:policy/{policy_name}"
                else:
                    raise e
                    

    elif event.get("op") == "delete":
        remove_policy(policy_arn)

def remove_policy(policy_arn):

    iam_client = boto3.client("iam")

    try:
        iam_client.get_policy(
            PolicyArn = policy_arn
        )

    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntityException':
            return "Something useful"
        elif e.response['Error']['Code'] == 'ServiceFailureException':
            return "something that says call me again"
        else:
            raise e

    policy_groups, policy_users, policy_roles = get_all_entities_for_policy(policy_arn)

    for group in policy_groups:
        try:
            iam_client.detach_group_policy(
                GroupName = group.get("GroupName"),
                PolicyArn = policy_arn
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                pass
            elif e.response['Error']['Code'] == 'ServiceFailureException':
                return "something that says call me again"
            else:
                raise e

    for user in policy_users:
        try:
            iam_client.detach_user_policy(
                UserName = user.get("UserName"),
                PolicyArn = policy_arn
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                pass
            elif e.response['Error']['Code'] == 'ServiceFailureException':
                return "something that says call me again"
            else:
                raise e

    for role in policy_roles:
        try:
            iam_client.detach_role_policy(
                RoleName = role.get("RoleName"),
                PolicyArn = policy_arn
            )
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntityException':
                pass
            elif e.response['Error']['Code'] == 'ServiceFailureException':
                return "something that says call me again"
            else:
                raise e

    response = iam_client.list_policy_versions(
        PolicyArn = policy_arn,
        MaxItems = 10
    )

    versions = response.get("Versions")

    if versions:
        for version in versions:
            if not version.get("IsDefaultVersion"):
                iam_client.delete_policy_version(
                    PolicyArn = policy_arn,
                    VersionId = version['VersionId']
                )

    iam_client.delete_policy(
        PolicyArn = policy_arn
    )


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

    

