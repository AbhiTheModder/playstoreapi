#!/bin/bash

REPO_SRC="https://gitlab.com/AuroraOSS/gplayapi"
REPO_LOCAL="/tmp/psapi"
RES_DIR="${REPO_LOCAL}/lib/src/main/res/raw"

DEVS_FILE="./playstoreapi/device.properties"

command -v git >/dev/null 2>&1 || {
    echo "git not installed"
    exit 1
}

if [ ! -d "./playstoreapi" ]; then
    echo "No playstoreapi dir found! Make sure you're in googleplay-api root dir"
    exit 1
fi

echo "==> Cloning play-store-api repo into $REPO_LOCAL"
git clone $REPO_SRC $REPO_LOCAL --depth=1 &>/dev/null

for dev in "$RES_DIR"/*; do
    if [[ $dev == *.properties ]]; then
        NAME=$(basename "$dev" | sed -e "s/\(.*\).properties/\1/")
        if grep -q "\[${NAME}\]" "$DEVS_FILE"; then
            echo "==> skipping device $NAME, already exists"
        else
            echo "==> appending device data for $NAME"
            {
                echo -e "\n[$NAME]"
                cat "$dev"
            } >>$DEVS_FILE
        fi
    fi
done

# cleanup
echo "==> Cleanup"
rm -rf $REPO_LOCAL