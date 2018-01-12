FROM python:3-alpine
WORKDIR /usr/src/app

# Install build time dependencies for uwsgi
# Install uwsgi and dumb-init
RUN apk --no-cache add --virtual build-deps \
    build-base bash linux-headers openssl-dev pcre-dev libffi-dev && \
    pip install dumb-init

# COPY tar.gz from build container
# Install it

COPY dist/. .
RUN bash -c "pip install *"

# Remove build time dependencies
# Install runtime dependencies
RUN apk del build-deps && \
    apk --no-cache add openssl pcre libffi ca-certificates

# add entrypoint
COPY docker/menu/docker-entrypoint.sh /bin/docker-entrypoint.sh

ENTRYPOINT ["/bin/docker-entrypoint.sh"]