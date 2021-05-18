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

ARG AWS_ACCOUNT
ARG AWS_REGION
ARG IMAGE_REPO
FROM 743260755741.dkr.ecr.eu-west-1.amazonaws.com/rstudio_image_build_openssh_image:latest

ENV TZ=Europe/London
ENV DEBIAN_FRONTEND noninteractive
ENV S6_VERSION=${S6_VERSION:-v2.1.0.2}

RUN apt update \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
     wget \
     tzdata \
     git \
     logrotate \
  && apt install  openssh-server git vim sudo -y \
  && git config --system credential.helper 'cache --timeout=3600' \
  && git config --system push.default simple \
  ## Set up S6 init system
  && wget -P /tmp/ https://github.com/just-containers/s6-overlay/releases/download/${S6_VERSION}/s6-overlay-amd64.tar.gz \
  && tar xzf /tmp/s6-overlay-amd64.tar.gz -C / --exclude='./bin' \
  && tar xzf /tmp/s6-overlay-amd64.tar.gz -C /usr ./bin \
  && sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/g' /etc/ssh/sshd_config  \
  && echo "AuthorizedKeysFile .ssh/authorized_keys" >> /etc/ssh/sshd_config

COPY root /

EXPOSE 22

CMD ["/init"]