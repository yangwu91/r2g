#!/bin/bash

#==============================================
# OpenShift or non-sudo environments support
# https://docs.openshift.com/container-platform/3.11/creating_images/guidelines.html#openshift-specific-guidelines
#==============================================

#if ! whoami &> /dev/null; then
#  if [ -w /etc/passwd ]; then
#    echo "${USER_NAME:-default}:x:$(id -u):0:${USER_NAME:-default} user:${HOME}:/sbin/nologin" >> /etc/passwd
#  fi
#fi

nohup /usr/bin/supervisord --configuration /etc/supervisord.conf > /var/log/supervisor/supervisord."$(date +%m%d%Y-%H%M%S)".log 2>&1 &

SUPERVISOR_PID=$!

echo "Supervising xvfb and selenium-standalone.jar running in background. PID: ${SUPERVISOR_PID}."
echo "###########################################################################"

#function shutdown {
#    echo "Trapped SIGTERM/SIGINT/x so shutting down supervisord..."
#    kill -s SIGTERM ${SUPERVISOR_PID}
#    wait ${SUPERVISOR_PID}
#    echo "Shutdown complete"
#}

#trap shutdown SIGTERM SIGINT
#wait ${SUPERVISOR_PID}
#printf '/LIBS/GUID = "%s"\n' `uuidgen` > ${HOME}/.ncbi/user-settings.mkfg

if [ "$1" == "debug" ]; then
    /bin/bash
else
    /opt/miniconda3/bin/r2g "$@"
fi

exit;

