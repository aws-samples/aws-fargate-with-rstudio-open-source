#!/usr/bin/with-contenv bash

######################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# OFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
######################################################################################

echo "creating user ..."

USER_NAME=${USER_NAME:-sshuser}

PUID=${PUID:-911}

groupadd $USER_NAME

cd /home

rm -rf $USER_NAME

useradd -rm -d /home/$USER_NAME -s /bin/bash -g $USER_NAME -G root -u $PUID $USER_NAME 

usermod -aG sudo $USER_NAME

echo "configuring ssh ..."

USER_NAME=${USER_NAME:-sshuser}
echo "User name is set to $USER_NAME"

# create folders
rm -rf /home/$USER_NAME/.ssh
rm -rf /home/$USER_NAME/ssh_host_keys
rm -rf /home/$USER_NAME/logs
mkdir -p \
    /home/$USER_NAME/{.ssh,ssh_host_keys}

mkdir -p var/run/logs/openssh

# set password for abc to unlock it and set sudo access
sed -i "/${USER_NAME} ALL.*/d" /etc/sudoers
if [ "$SUDO_ACCESS" == "true" ]; then
    if [ -n "$USER_PASSWORD" ] || [ -n "$USER_PASSWORD_FILE" -a -f "$USER_PASSWORD_FILE" ]; then
        echo "${USER_NAME} ALL=(ALL) ALL" >> /etc/sudoers
        echo "Sudo is enabled with password."
    else
        echo "${USER_NAME} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
        echo "Sudo is enabled without password."
    fi
else
    echo "Sudo is disabled."
fi
[[ -n "$USER_PASSWORD_FILE" ]] && [[ -f "$USER_PASSWORD_FILE" ]] && \
    USER_PASSWORD=$(cat "$USER_PASSWORD_FILE") && \
    echo "User password is retrieved from file."
USER_PASSWORD=${USER_PASSWORD:-$(< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c${1:-8};echo;)}
echo "${USER_NAME}:${USER_PASSWORD}" | chpasswd

# symlink out ssh config directory
if [ ! -L /etc/ssh ];then
    if [ ! -f /home/$USER_NAME/ssh_host_keys/sshd_config ]; then
        sed -i '/#PidFile/c\PidFile \/home/$USER_NAME\/sshd.pid' /etc/ssh/sshd_config
        cp -a /etc/ssh/sshd_config /home/$USER_NAME/ssh_host_keys/
    fi
    rm -Rf /etc/ssh
    ln -s /home/$USER_NAME/ssh_host_keys /etc/ssh
    ssh-keygen -A
    ls -l /home/$USER_NAME/ssh_host_keys/*
fi

# password access
if [ "$PASSWORD_ACCESS" == "true" ]; then
    sed -i '/^#PasswordAuthentication/c\PasswordAuthentication yes' /etc/ssh/sshd_config
    sed -i '/^PasswordAuthentication/c\PasswordAuthentication yes' /etc/ssh/sshd_config
    chown root:"${USER_NAME}" \
        /etc/shadow
    echo "User/password ssh access is enabled."
else
    sed -i '/^PasswordAuthentication/c\PasswordAuthentication no' /etc/ssh/sshd_config
    chown root:root \
        /etc/shadow
    echo "User/password ssh access is disabled."
fi

# set umask for sftp
UMASK=${UMASK:-022}
sed -i "s|/usr/lib/ssh/sftp-server$|/usr/lib/ssh/sftp-server -u ${UMASK}|g" /etc/ssh/sshd_config

# set key auth in file
if [ ! -f /home/$USER_NAME/.ssh/authorized_keys ];then
    touch /home/$USER_NAME/.ssh/authorized_keys
fi

[[ -n "$PUBLIC_KEY" ]] && \
    [[ ! $(grep "$PUBLIC_KEY" /home/$USER_NAME/.ssh/authorized_keys) ]] && \
    echo "$PUBLIC_KEY" >> /home/$USER_NAME/.ssh/authorized_keys && \
    echo "Public key from env variable added"

[[ -n "$PUBLIC_KEY_FILE" ]] && [[ -f "$PUBLIC_KEY_FILE" ]] && \
    PUBLIC_KEY2=$(cat "$PUBLIC_KEY_FILE") && \
    [[ ! $(grep "$PUBLIC_KEY2" /home/$USER_NAME/.ssh/authorized_keys) ]] && \
    echo "$PUBLIC_KEY2" >> /home/$USER_NAME/.ssh/authorized_keys && \
    echo "Public key from file added"

# back up old log files processed by logrotate
[[ -f /home/$USER_NAME/logs/openssh/openssh.log ]] && \
    mv /home/$USER_NAME/logs/openssh /home/$USER_NAME/logs/openssh.old.logs && \
    mkdir -p /home/$USER_NAME/logs/openssh

# add log file info
[[ ! -f /home/$USER_NAME/logs/loginfo.txt ]] && \
    echo "The current log file is named \"current\". The rotated log files are gzipped, named with a TAI64N pipeline_unique_id and a \".s\" extension" > /var/run/logs/loginfo.txt

# permissions
chown -R "${USER_NAME}":"${USER_NAME}" \
    /home/$USER_NAME
chmod go-w \
    /home/$USER_NAME
chmod 700 \
    /home/$USER_NAME/.ssh
chmod 600 \
    /home/$USER_NAME/.ssh/authorized_keys

cd /var/run

chown -R "${USER_NAME}":"${USER_NAME}" \
    logs/openssh

echo "Starting ssh server..."

sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/g' /etc/ssh/sshd_config  
echo "AuthorizedKeysFile .ssh/authorized_keys" >> /etc/ssh/sshd_config

service ssh start

