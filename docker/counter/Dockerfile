FROM python:3-alpine
WORKDIR /usr/src/app

COPY . .
RUN apk -U add git && python setup.py bdist_wheel

FROM python:3-alpine
WORKDIR /usr/src/app

# Install build time dependencies for uwsgi
# Install uwsgi and dumb-init
RUN apk --no-cache add --virtual build-deps \
    build-base bash linux-headers openssl-dev pcre-dev libffi-dev && \
    pip install uwsgi dumb-init

# COPY tar.gz from build container
# Install it
# COPY over wsgi configuration
COPY --from=0 /usr/src/app/dist/. .
RUN bash -c "pip install *"
COPY docker/counter/wsgi.ini wsgi.ini

# Remove build time dependencies
# Install runtime dependencies
RUN apk del build-deps && \
    apk --no-cache add openssl pcre libffi ca-certificates

# add entrypoint
COPY docker/counter/docker-entrypoint.sh /bin/docker-entrypoint.sh

ENTRYPOINT ["/bin/docker-entrypoint.sh"]