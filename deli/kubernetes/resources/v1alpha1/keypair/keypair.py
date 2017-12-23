from deli.kubernetes.resources.model import ProjectResourceModel


class Keypair(ProjectResourceModel):

    def __init__(self, raw=None):
        super().__init__(raw)
        if raw is None:
            self._raw['spec'] = {
                'publicKey': None
            }

    @property
    def public_key(self):
        return self._raw['spec']['publicKey']

    @public_key.setter
    def public_key(self, value):
        self._raw['spec']['publicKey'] = value
