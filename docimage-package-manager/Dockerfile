ARG R_VERSION=3.6.2
FROM rstudio/r-base:${R_VERSION}-bionic
LABEL maintainer="RStudio Docker <docker@rstudio.com>"

# Locale configuration --------------------------------------------------------#
RUN localedef -i en_US -f UTF-8 en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

# hadolint ignore=DL3008,DL3009
RUN apt-get update --fix-missing \
    && apt-get install -y --no-install-recommends \
        gdebi-core \
        libssl1.0.0 \
        libssl-dev \
	sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /var/run/rstudio-pm
ENV PATH /opt/rstudio-pm/bin:$PATH

# Runtime settings ------------------------------------------------------------#
ARG TINI_VERSION=0.18.0
RUN curl -L -o /usr/local/bin/tini https://github.com/krallin/tini/releases/download/v${TINI_VERSION}/tini && \
    chmod +x /usr/local/bin/tini

COPY ./docimage-package-manager/startup.sh /usr/local/bin/startup.sh
RUN chmod +x /usr/local/bin/startup.sh

EXPOSE 4242/tcp
EXPOSE 2112/tcp

# Download RStudio Package Manager ---------------------------------------------#
ARG RSPM_VERSION=2021.09.0-1
ARG RSPM_DOWNLOAD_URL=https://cdn.rstudio.com/package-manager/ubuntu/amd64
RUN apt-get update --fix-missing \
    && curl -O ${RSPM_DOWNLOAD_URL}/rstudio-pm_${RSPM_VERSION}_amd64.deb \
    && gdebi -n rstudio-pm_${RSPM_VERSION}_amd64.deb \
    && rm rstudio-pm_${RSPM_VERSION}_amd64.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /opt/rstudio-pm/bin/rspm /usr/local/bin/rspm

#ENV RSPM_LICENSE ""
ENV RSPM_LICENSE_SERVER ""
COPY ./docimage-package-manager/rstudio-pm.gcfg /etc/rstudio-pm/rstudio-pm.gcfg
#VOLUME ["/data"]

ENTRYPOINT ["tini", "--"]
CMD ["/usr/local/bin/startup.sh"]
