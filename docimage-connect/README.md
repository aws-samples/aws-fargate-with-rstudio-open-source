# RStudio Connect

Docker images for RStudio Professional Products

**IMPORTANT:** There are a few things you need to know before using these images:

1. These images are provided as a convenience to RStudio customers and are not formally supported by RStudio. If you
   have questions about these images, you can ask them in the issues in the repository or to your support
   representative, who will route them appropriately.
1. Outdated images will be removed periodically from DockerHub as product version updates are made. Please make plans to
   update at times or use your own build of the images.
1. These images are meant as a starting point for your needs. Consider creating a fork of this repo, where you can
   continue to merge in changes we make while having your own security scanning, base OS in use, or other custom
   changes. We
   provide [instructions for building](https://github.com/rstudio/rstudio-docker-products#instructions-for-building) for
   these cases.

#### Simple Example

To verify basic functionality as a first step:

```
# Replace with valid license
export RSC_LICENSE=XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX

# Run without persistent data and using default configuration
docker run -it --privileged \
    -p 3939:3939 \
    -e RSC_LICENSE=$RSC_LICENSE \
    rstudio/rstudio-connect:latest
```

Open [http://localhost:3939](http://localhost:3939) to access RStudio Connect.

For a more "real" deployment, continue reading!

#### Overview

This Docker container is built following
the [RStudio Connect admin guide](https://docs.rstudio.com/connect/admin/index.html), please
see [Server Guide/Docker](https://docs.rstudio.com/connect/admin/server-management/#docker) for more details on the
requirements and how to extend this image.

This container includes:

1. R 3.6.1
2. Python 3.6.5
3. RStudio Connect

Note that running the RStudio Connect Docker image requires the container to run using the `--privileged` flag and a
valid RStudio Connect license.

> IMPORTANT: to use RStudio Connect with more than one user, you will need to
> define `Server.Address` in the `rstudio-connect.gcfg` file. To do so, update
> your configuration file with the URL that users will use to visit Connect.
> Then start or restart the container.

#### Configuration

The configuration of RStudio Connect is made on the `/etc/rstudio-connect/rstudio-connect.gcfg` file, mount this file as
volume with an external file on the host machine to change the configuration and restart the container for changes to
take effect.

Be sure the config file has these fields:

- `Server.Address` set to the exact URL that users will use to visit Connect. A
  placeholder `http://localhost:3939` is in use by default
- `Server.DataDir` set to `/data/`
- `HTTP.Listen` (or equivalent `HTTP`, `HTTPS`, or `HTTPRedirect` settings. This could change how you should configure the container ports)
- `Python.Enabled` and `Python.Executable`

See a complete example of that file at `connect/rstudio-connect.gcfg`.

#### Persistent Data

In order to persist RSC metadata and app data between container restarts configure RSC `Server.DataDir` option to go to
a persistent volume. 

The included configuration file expects a persistent volume from the host machine or your docker
orchestration system to be available at `/data`. Should you wish to move this to a different path, you can change the
`Server.DataDir` option.

#### Licensing

Using the RStudio Connect docker image requires to have a valid License. You can set the RSC license in three ways:

1. Setting the `RSC_LICENSE` environment variable to a valid license key inside the container
2. Setting the `RSC_LICENSE_SERVER` environment variable to a valid license server / port inside the container
3. Mounting a `/etc/rstudio-connect/license.lic` single file that contains a valid license for RStudio Connect

**NOTE:** the "offline activation process" is not supported by this image today. Offline installations will need
to explore using a license server, license file, or custom image with manual intervention.

#### Environment variables

| Variable | Description | Default |
|-----|---|---|
| `RSC_LICENSE` | License key for RStudio Connect, format should be: `XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX` | None |
| `RSC_LICENSE_SERVER` | Floating license server, format should be: `my.url.com:port` | None |

#### Ports

| Variable | Description |
|-----|---|
| `3939` | Default HTTP Port for RStudio Connect |

#### Example usage

```bash
# Replace with valid license
export RSC_LICENSE=XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX

# Run without persistent data and using an external configuration
docker run -it --privileged \
    -p 3939:3939 \
    -v $PWD/connect/rstudio-connect.gcfg:/etc/rstudio-connect/rstudio-connect.gcfg \
    -e RSC_LICENSE=$RSC_LICENSE \
    rstudio/rstudio-connect:latest

# Run with persistent data and using an external configuration
docker run -it --privileged \
    -p 3939:3939 \
    -v $PWD/data/rsc:/data \
    -v $PWD/connect/rstudio-connect.gcfg:/etc/rstudio-connect/rstudio-connect.gcfg \
    -e RSC_LICENSE=$RSC_LICENSE \
    rstudio/rstudio-connect:latest
```

Open [http://localhost:3939](http://localhost:3939) to access RStudio Connect.

# Licensing

The license associated with the RStudio Docker Products repository is located [in LICENSE.md](https://github.com/rstudio/rstudio-docker-products/blob/main/LICENSE.md).

As is the case with all container images, the images themselves also contain other software which may be under other
licenses (i.e. bash, linux, system libraries, etc., along with any other direct or indirect dependencies of the primary
software being contained).

It is an image user's responsibility to ensure that use of this image (and any of its dependent layers) complies with
all relevant licenses for the software contained in the image.
