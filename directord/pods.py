#   Copyright Peznauts <kevin@cloudnull.com>. All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

import json
import os
import yaml

try:
    from podman import PodmanClient

    AVAILABLE_PODMAN = True
except ImportError:
    AVAILABLE_PODMAN = False


class PodmanConnect(object):
    """Connect to the podman unix socket."""

    def __init__(self, socket="/var/run/podman/podman.sock"):
        """Initialize the Directord pod connection class.

        Sets up the pod api object.

        :param socket: Socket path to connect to.
        :type socket: String
        """

        self.pod = PodmanClient("unix://{socket}".format(socket=socket))
        self.api = self.pod.api

    def __exit__(self, *args, **kwargs):
        """Close the connection and exit."""

        self.close()

    def __enter__(self):
        """Return self for use within a context manager."""

        return self

    def close(self):
        """Close the connection."""

        self.pod.close()


class PodmanPod(PodmanConnect):
    def __init__(self, socket):
        """Initialize the Directord pod class.

        Sets up the pod api object.

        :param socket: Socket path to connect to.
        :type socket: String
        """

        super(PodmanPod, self).__init__(socket=socket)

    @staticmethod
    def _decode(data):
        """Decode byte data and return it.

        If the byte data is JSON type the returned value will
        be a JSON string.
        """

        data = data.decode()
        if data:
            try:
                return json.loads(data)
            except Exception:
                return data

    def start(self, name, timeout=120):
        """Start a given pod and return the action status.

        :param name: Pod name.
        :type name: String
        :param timeout: API timeout when running a pod interaction.
        :type timeout: Integer
        :returns: Tuple
        """

        resp = self.api.post(
            path="/pods/{name}/start".format(name=name),
            params={"t": timeout},
        )
        return resp.ok, self._decode(resp.content)

    def stop(self, name, timeout=120):
        """Stop a given pod and return the action status.

        :param name: Pod name.
        :type name: String
        :param timeout: API timeout when running a pod interaction.
        :type timeout: Integer
        :returns: Tuple
        """

        resp = self.api.post(
            path="/pods/{name}/stop".format(name=name),
            params={"t": timeout},
        )
        return resp.ok, self._decode(resp.content)

    def rm(self, name, force=False):
        """Remove a given pod and return the action status.

        :param name: Pod name.
        :type name: String
        :param force: Force remove a pod
        :type force: Boolean
        :returns: Tuple
        """

        resp = self.api.delete(
            path="/pods/{name}".format(name=name),
            params={"force": force},
        )
        return resp.ok, self._decode(resp.content)

    def kill(self, name, signal="SIGKILL"):
        """Kill a given pod and return the action status.

        :param name: Pod name.
        :type name: String
        :param signal: Signal used when killing a pod
        :type signal: String
        :returns: Tuple
        """

        resp = self.api.post(
            path="/pods/{name}/kill".format(name=name),
            params={"signal": signal},
        )
        return resp.ok, self._decode(resp.content)

    def inspect(self, name):
        """Inspect a given pod and return the action status.

        :param name: Pod name.
        :type name: String
        :returns: Tuple
        """

        resp = self.api.get(path="/pods/{name}/json".format(name=name))
        return resp.ok, self._decode(resp.content)

    def play(self, pod_file, tls_verify=True):
        """Instantiate a given pod and return the action status.

        :param pod_file: Full path to a pod YAML file.
        :type pod_file: String
        :returns: Tuple
        """

        if os.path.exists(os.path.abspath(os.path.expanduser(pod_file))):
            with open(pod_file) as f:
                resp = self.api.post(
                    path="/play/kube",
                    data=json.dumps(yaml.safe_load(f)),
                    params={"tlsVerify": tls_verify, "start": True},
                )
            return resp.ok, self._decode(resp.content)
        else:
            return False, "Pod YAML did not exist"

    def exec_run(self, name, command, env, privileged=False):
        """Create an exec container and run it.

        :param name: Container name.
        :type name: String
        :param command: Command to be run in list format.
        :type command: List
        :param env: Environment used when executing a command.
        :type env: List
        :param privileged: Enable|Disable privileged commands.
        :type privileged: Boolean
        :returns: Tuple
        """

        _command = {
            "AttachStderr": True,
            "AttachStdin": True,
            "AttachStdout": True,
            "Cmd": command,
            "Env": env,
            "Privileged": privileged,
            "Tty": True,
        }
        resp = self.api.post(
            path="containers/{name}/exec".format(name=name),
            data=json.dumps(_command),
        )
        if resp.ok:
            resp = self.api.post(
                path="/exec/{id}/start".format(
                    id=self._decode(resp.content)["Id"]
                ),
                data=json.dumps({"Detach": False, "Tty": True}),
            )
        return resp.ok, self._decode(resp.content)
