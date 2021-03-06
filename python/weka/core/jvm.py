# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# jvm.py
# Copyright (C) 2014-2019 Fracpete (pythonwekawrapper at gmail dot com)

import javabridge
import os
import glob
import logging


started = None
""" whether the JVM has been started """

with_package_support = None
""" whether JVM was started with package support """

# logging setup
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def lib_dir():
    """
    Returns the "lib" directory path.

    :return: the path to the "lib" directory
    :rtype: str
    """

    rootdir = os.path.split(os.path.dirname(__file__))[0]
    return rootdir + os.sep + "lib"


def add_bundled_jars():
    """
    Adds the bundled jars to the JVM's classpath.
    """
    # determine lib directory with jars
    libdir = lib_dir()

    # add jars from lib directory
    for l in glob.glob(libdir + os.sep + "*.jar"):
        if l.lower().find("-src.") == -1:
            javabridge.JARS.append(str(l))


def add_system_classpath():
    """
    Adds the system's classpath to the JVM's classpath.
    """
    if 'CLASSPATH' in os.environ:
        parts = os.environ['CLASSPATH'].split(os.pathsep)
        for part in parts:
            javabridge.JARS.append(part)


def start(class_path=None, bundled=True, packages=False, system_cp=False, max_heap_size=None):
    """
    Initializes the javabridge connection (starts up the JVM).

    :param class_path: the additional classpath elements to add
    :type class_path: list
    :param bundled: whether to add jars from the "lib" directory
    :type bundled: bool
    :param packages: whether to add jars from Weka packages as well (bool) or an alternative Weka home directory (str)
    :type packages: bool or str
    :param system_cp: whether to add the system classpath as well
    :type system_cp: bool
    :param max_heap_size: the maximum heap size (-Xmx parameter, eg 512m or 4g)
    :type max_heap_size: str
    """
    global started
    global with_package_support

    if started is not None:
        logger.info("JVM already running, call jvm.stop() first")
        return

    # add user-defined jars first
    if class_path is not None:
        for cp in class_path:
            logger.debug("Adding user-supplied classpath=" + cp)
            javabridge.JARS.append(cp)

    if bundled:
        logger.debug("Adding bundled jars")
        add_bundled_jars()

    if system_cp:
        logger.debug("Adding system classpath")
        add_system_classpath()

    logger.debug("Classpath=" + str(javabridge.JARS))
    logger.debug("MaxHeapSize=" + ("default" if (max_heap_size is None) else max_heap_size))

    args = []
    weka_home = None
    if packages is not None:
        if isinstance(packages, bool):
            if packages:
                with_package_support = True
                logger.debug("Package support enabled")
            else:
                logger.debug("Package support disabled")
                args.append("-Dweka.packageManager.loadPackages=false")
        if isinstance(packages, str):
            if os.path.exists(packages) and os.path.isdir(packages):
                logger.debug("Using alternative Weka home directory: " + packages)
                weka_home = packages
                with_package_support = True
            else:
                logger.warning("Invalid Weka home: " + packages)

    javabridge.start_vm(args=args, run_headless=True, max_heap_size=max_heap_size)
    javabridge.attach()
    started = True

    if weka_home is not None:
        from weka.core.classes import Environment
        env = Environment.system_wide()
        logger.debug("Using alternative Weka home directory: " + packages)
        env.add_variable("WEKA_HOME", weka_home)

    # initialize package manager
    javabridge.static_call(
        "Lweka/core/WekaPackageManager;", "loadPackages",
        "(Z)V",
        False)


def stop():
    """
    Kills the JVM.
    """
    global started
    if started is not None:
        started = None
        javabridge.kill_vm()
