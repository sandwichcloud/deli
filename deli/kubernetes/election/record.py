import json

from kubernetes import client
from kubernetes.client.rest import ApiException

from deli.kubernetes.resources.const import GROUP


class ElectionRecord(object):

    def __init__(self, raw=None):
        if raw is None:
            raw = {
                "apiVersion": "v1",
                "kind": "Endpoints",
                "metadata": {
                    "annotations": {
                        GROUP + "/leader": "",
                    },
                    "name": "sandwich-controller"
                }
            }
        self._raw = raw

    def create(self):
        core_api = client.CoreV1Api()
        self._raw = core_api.create_namespaced_endpoints("kube-system", self._raw).to_dict()

    @classmethod
    def get(cls, safe=True):
        core_api = client.CoreV1Api()
        try:
            resp = core_api.read_namespaced_endpoints("sandwich-controller", "kube-system").to_dict()
            if resp is None:
                return None
        except ApiException as e:
            if e.status == 404 and safe:
                return None
            raise
        return cls(resp)

    def update(self):
        core_api = client.CoreV1Api()
        core_api.patch_namespaced_endpoints("sandwich-controller", "kube-system", self._raw)

    @property
    def leader_data(self):
        leader_string = self._raw['metadata']['annotations'][GROUP + "/leader"]
        if leader_string == "":
            return {
                'identity': None,
                'lease_duration': None,
                'acquire_date': None,
                'renew_date': None,
                'leader_transitions': 0
            }
        return json.loads(leader_string)

    @leader_data.setter
    def leader_data(self, value):
        self._raw['metadata']['annotations'][GROUP + "/leader"] = json.dumps(value)

    @property
    def leader_identity(self):
        return self.leader_data['identity']

    @leader_identity.setter
    def leader_identity(self, value):
        leader_data = self.leader_data
        leader_data['identity'] = value
        self.leader_data = leader_data

    @property
    def lease_duration(self):
        return self.leader_data['lease_duration']

    @lease_duration.setter
    def lease_duration(self, value):
        leader_data = self.leader_data
        leader_data['lease_duration'] = value
        self.leader_data = leader_data

    @property
    def acquire_date(self):
        return self.leader_data['acquire_date']

    @acquire_date.setter
    def acquire_date(self, value):
        leader_data = self.leader_data
        leader_data['acquire_date'] = value
        self.leader_data = leader_data

    @property
    def renew_date(self):
        return self.leader_data['renew_date']

    @renew_date.setter
    def renew_date(self, value):
        leader_data = self.leader_data
        leader_data['renew_date'] = value
        self.leader_data = leader_data

    @property
    def leader_transitions(self):
        return self.leader_data['leader_transitions']

    @leader_transitions.setter
    def leader_transitions(self, value):
        leader_data = self.leader_data
        leader_data['leader_transitions'] = value
        self.leader_data = leader_data
