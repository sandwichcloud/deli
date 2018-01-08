FROM python:3-alpine
WORKDIR /usr/src/app

COPY . .
RUN apk -U add git && python setup.py bdist_wheel

FROM python:3-alpine
WORKDIR /usr/src/app

# Install build time dependencies for uwsgi
# Install dumb-init
RUN apk --no-cache add --virtual build-deps \
    build-base bash linux-headers pcre-dev libffi-dev && \
    pip install dumb-init

# COPY tar.gz from build container
# Install it
# TODO: this should be replaced by a build arg to install the correct version from pypi
COPY --from=0 /usr/src/app/dist/. .
RUN bash -c "pip install *"

# Remove build time dependencies
# Install runtime dependencies
RUN apk del build-deps && \
    apk --no-cache add openssl pcre libffi ca-certificates

# add entrypoint
COPY docker/menu/docker-entrypoint.sh /bin/docker-entrypoint.sh

ENTRYPOINT ["/bin/docker-entrypoint.sh"]