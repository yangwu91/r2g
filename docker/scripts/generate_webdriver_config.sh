#!/bin/bash

CHROME_VERSION=$(/usr/bin/google-chrome -version | awk '{ print $3 }')

cat <<_EOF
{
  "capabilities": [
    {
      "version": "$CHROME_VERSION",
      "browserName": "chrome",
      "maxInstances": $NODE_MAX_INSTANCES,
      "seleniumProtocol": "WebDriver",
      "applicationName": "$NODE_APPLICATION_NAME"
    }
  ],
  "proxy": "org.openqa.grid.selenium.proxy.DefaultRemoteProxy",
  "maxSession": $NODE_MAX_SESSION,
  "host": "$NODE_HOST",
  "port": $NODE_PORT,
  "register": true,
  "registerCycle": $NODE_REGISTER_CYCLE,
  "nodePolling": $NODE_POLLING,
  "unregisterIfStillDownAfter": $NODE_UNREGISTER_IF_STILL_DOWN_AFTER,
  "downPollingLimit": $NODE_DOWN_POLLING_LIMIT,
  "debug": $GRID_DEBUG
}
_EOF