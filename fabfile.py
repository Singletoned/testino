# -*- coding: utf-8 -*-

from fabric.api import local, abort
from fabric.contrib.console import confirm

import __metadata__

def clean():
    local("git clean -fdnx")
    if confirm("Shall I delete these files?", default=False):
        local("git clean -fdx")
    else:
        abort("Well I give up then!")

def version():
    version = __metadata__.data['version']
    print "Version:", version
    return version

def build():
    clean()
    version_number = version()
    bundle_name = "testino-%s.pybundle" % version_number
    local("pip bundle %s -r requirements.txt ." % bundle_name)

