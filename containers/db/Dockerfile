# Koji database image.
# Initializes a PostgreSQL instance with the Koji schema.
FROM postgres:16

ENV POSTGRES_DB=koji \
    POSTGRES_USER=koji \
    POSTGRES_PASSWORD=koji

# Copy the koji schema and the seed script into the init dir. The postgres
# entrypoint runs scripts in /docker-entrypoint-initdb.d on first init.
COPY --chown=postgres:postgres schemas/schema.sql /docker-entrypoint-initdb.d/01-schema.sql
COPY --chown=postgres:postgres containers/db/init-admin.sql /docker-entrypoint-initdb.d/02-admin.sql

EXPOSE 5432
