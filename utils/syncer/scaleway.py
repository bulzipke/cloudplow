import logging
import time

from utils import process

try:
    from shlex import quote as cmd_quote
except ImportError:
    from pipes import quote as cmd_quote

log = logging.getLogger("scaleway")


class Scaleway:
    NAME = 'Scaleway'

    def __init__(self, from_config, to_config, **kwargs):
        self.sync_from_config = from_config
        self.sync_to_config = to_config
        self.kwargs = kwargs
        self.instance_id = None

        # pass region from kwargs (default France)
        if 'region' in kwargs:
            self.region = kwargs['region']
        else:
            self.region = 'par1'
        # pass type from kwargs (default X64-2GB)
        if 'type' in kwargs:
            self.type = kwargs['type']
        else:
            self.type = 'X64-2GB'
        # pass image from kwargs (default Ubuntu 16.04)
        if 'image' in kwargs:
            self.image = kwargs['image']
        else:
            self.image = 'ubuntu-xenial'

        log.info("Initialized Scaleway syncer agent with kwargs: %r", kwargs)

    def startup(self, **kwargs):
        if 'name' not in kwargs:
            log.error("You must provide an name for this instance")
            return False, None

        # create instance
        log.debug("Creating new instance...")
        cmd = "scw --region=%s run -d --name=%s --ipv6 --commercial-type=%s %s" % (
            cmd_quote(self.region), cmd_quote(kwargs['name']), cmd_quote(self.type), cmd_quote(self.image))
        log.debug("Using: %s", cmd)

        resp = process.popen(cmd)
        if not resp or 'failed' in resp.lower():
            log.error("Unexpected response while creating instance: %s", resp)
            return False, self.instance_id
        else:
            self.instance_id = resp
        log.info("Created new instance: %r", self.instance_id)

        # wait for instance to finish booting
        log.info("Waiting for instance to finish booting...")
        time.sleep(10)
        cmd = "scw --region=%s exec -w %s %s" % (
            cmd_quote(self.region), cmd_quote(self.instance_id), cmd_quote('uname -a'))
        log.debug("Using: %s", cmd)

        resp = process.popen(cmd)
        if not resp or 'gnu/linux' not in resp.lower():
            log.error("Unexpected response while waiting for instance to boot: %s", resp)
            self.destroy()
            return False, self.instance_id

        log.info("Instance has finished booting, uname: %r", resp)
        return True, self.instance_id

    def setup(self):
        if not self.instance_id or '-' not in self.instance_id:
            log.error("Setup was called, but no instance_id was found, aborting...")
            return False

        # install unzip
        cmd_exec = "apt-get -qq update && apt-get -y -qq install unzip"
        cmd = "scw --region=%s exec %s %s" % (cmd_quote(self.region), cmd_quote(self.instance_id), cmd_quote(cmd_exec))
        log.debug("Using: %s", cmd)

        resp = process.popen(cmd)
        if not resp or 'setting up unzip' not in resp.lower():
            log.error("Unexpected response while installing unzip: %s", resp)
            self.destroy()
            return False
        log.info("Installed unzip")

        # install rclone to instance
        cmd_exec = "curl -sO https://downloads.rclone.org/rclone-current-linux-amd64.zip && " \
                   "unzip -q rclone-current-linux-amd64.zip && cd rclone-*-linux-amd64 && " \
                   "cp rclone /usr/bin/ && chown root:root /usr/bin/rclone && chmod 755 /usr/bin/rclone && " \
                   "mkdir -p /root/.config/rclone && which rclone"
        cmd = "scw --region=%s exec %s %s" % (cmd_quote(self.region), cmd_quote(self.instance_id), cmd_quote(cmd_exec))
        log.debug("Using: %s", cmd)

        resp = process.popen(cmd)
        if not resp or '/usr/bin/rclone' not in resp.lower():
            log.error("Unexpected response while installing rclone: %s", resp)
            self.destroy()
            return False
        log.info("Installed rclone")

        # copy rclone.conf to instance

        return False

    def destroy(self):
        if not self.instance_id or '-' not in self.instance_id:
            log.error("Destroy was called, but no instance_id was found, aborting...")
            return False

        # destroy the instance
        cmd = "scw --region=%s rm -f %s" % (cmd_quote(self.region), cmd_quote(self.instance_id))
        log.debug("Using: %s", cmd)

        resp = process.popen(cmd)
        if not resp or self.instance_id.lower() not in resp.lower():
            log.error("Unexpected response while destroying instance %r: %s", self.instance_id, resp)
            return False

        log.info("Destroyed instance: %r", self.instance_id)
        return True

    def sync(self):
        # run rclone sync
        pass
