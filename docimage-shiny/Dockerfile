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

FROM rocker/r-ver:4.1.0

ENV S6_VERSION=v2.1.0.2
ENV PATH=/usr/lib/rstudio-server/bin:$PATH
ENV SHINY_SERVER_VERSION=latest
ENV PANDOC_VERSION=default
ENV ROOT=TRUE
ENV AWS_ACCOUNT=${AWS_ACCOUNT}
ENV AWS_REGION=${AWS_REGION}

COPY ./docimage-shiny/rocker_scripts /rocker_scripts

RUN chmod 755 /rocker_scripts/*

RUN /rocker_scripts/install_pandoc.sh
RUN /rocker_scripts/install_shiny_server.sh
RUN /rocker_scripts/install_tidyverse.sh

EXPOSE 3838

CMD ["/init"]
