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

ENV AWS_S3_BUCKET=${AWS_S3_BUCKET}
ENV AWS_ACCESS_KEY_ID=""
ENV AWS_ACCESS_KEY=""
ENV AWS_ATHENA_WG=${AWS_ATHENA_WG}
ENV ROOT ${ROOT}
ENV ADD ${ADD}
ENV S6_VERSION "v2.1.0.2"
ENV RSTUDIO_VERSION=1.4.1717
ENV PATH /usr/lib/rstudio-server/bin:$PATH
ENV SHINY_SERVER_VERSION latest
ENV PANDOC_VERSION default

COPY ./docimage-rstudio/rocker_scripts /rocker_scripts
COPY ./docimage-rstudio/user_scripts /usr/local/bin/user_scripts

RUN chmod 755 /rocker_scripts/*
RUN chmod 755 /usr/local/bin/user_scripts/*

RUN /rocker_scripts/install_rstudio.sh
RUN /rocker_scripts/install_pandoc.sh
RUN /rocker_scripts/install_shiny_server.sh
RUN /rocker_scripts/install_tidyverse.sh

RUN Rscript /usr/local/bin/user_scripts/install_packages.R

EXPOSE 8787
EXPOSE 3838

CMD ["/init"]
