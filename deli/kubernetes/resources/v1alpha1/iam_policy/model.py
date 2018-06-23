from deli.kubernetes.resources.model import SystemResourceModel


class IAMPolicy(SystemResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                "bindings": []
            }

    @property
    def bindings(self):
        return self._raw['spec']['bindings']

    @bindings.setter
    def bindings(self, value):
        self._raw['spec']['bindings'] = value

    @classmethod
    def create_system_policy(cls):
        policy = cls()
        policy.name = "system"
        policy.bindings = [
            {
                "role": "admin",
                "members": [
                    "serviceAccount:admin@service-account.system.sandwich.local"
                ]
            }
        ]
        if policy.get("system") is None:
            policy.create()

    @classmethod
    def create_project_policy(cls, project, token):
        policy = cls()
        policy.name = project.name

        if token.service_account is not None:
            member_email = "serviceAccount:" + token.email
        else:
            member_email = "user:" + token.email

        policy.bindings = [
            {
                "role": "owner",
                "members": [member_email]
            }
        ]
        policy.create()
