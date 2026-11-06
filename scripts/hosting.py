"""OVH SFTP connection; credentials are supplied only in environment variables."""
import base64
import hashlib
import os
import paramiko

FINGERPRINT = 'xhieLplnoEvvl7+a8sq8wLCh/bvOQvQFIVewi+fK2og='

class PinnedKey(paramiko.MissingHostKeyPolicy):
    def missing_host_key(self, client, hostname, key):
        actual=base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode()
        if actual != FINGERPRINT:
            raise paramiko.SSHException('The OVH SSH host key changed; refusing connection.')

def connect():
    client=paramiko.SSHClient()
    client.set_missing_host_key_policy(PinnedKey())
    client.connect(os.environ['SITE_FTP_HOST'],username=os.environ['SITE_FTP_USER'],
                   password=os.environ['SITE_FTP_PASSWORD'],look_for_keys=False,
                   allow_agent=False,timeout=20,auth_timeout=20)
    return client
