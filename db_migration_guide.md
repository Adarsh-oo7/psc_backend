# Database Migration Guide: SQLite to PostgreSQL

This guide outlines the steps to safely migrate all questions, topics, exams, and user data from the local SQLite database (`db.sqlite3`) to a production PostgreSQL database.

---

## Prerequisites

1. Ensure **PostgreSQL** is installed and running on your database server (local or cloud).
2. Create a clean database and database user:
   ```sql
   CREATE DATABASE kpsc_db;
   CREATE USER kpsc_user WITH PASSWORD 'your-secure-password';
   GRANT ALL PRIVILEGES ON DATABASE kpsc_db TO kpsc_user;
   ```
3. Make sure the database driver `psycopg2-binary` is installed (already verified on this system).

---

## Step 1: Export Data from SQLite

Dump the SQLite data to a JSON file. We exclude standard system permission models to avoid key conflicts upon import:

```bash
python manage.py dumpdata --exclude auth.Permission --exclude contenttypes --indent 2 > db_dump.json
```

---

## Step 2: Configure PostgreSQL Connection

Open your `psc_backend/.env` file and replace the SQLite database URL with your PostgreSQL connection string:

```env
# Comment out SQLite
# DATABASE_URL=sqlite:///db.sqlite3

# Enable PostgreSQL
DATABASE_URL=postgresql://kpsc_user:your-secure-password@localhost:5432/kpsc_db
```

---

## Step 3: Run Database Migrations on PostgreSQL

Create the clean table schemas in your PostgreSQL database:

```bash
python manage.py migrate
```

---

## Step 4: Import Data into PostgreSQL

Load the dumped SQLite data into PostgreSQL:

```bash
python manage.py loaddata db_dump.json
```

---

## Step 5: Reset Auto-Incrementing Primary Key Sequences

When importing data with explicit primary keys (`id`), PostgreSQL's internal auto-increment sequences (e.g. `id_seq`) do not update automatically. This will cause future database inserts (like creating a user, adding a comment, or saving a question) to fail with a `duplicate key value violates unique constraint` error.

To fix this, reset the database sequences for all apps:

### Option A: Via Python Shell (Recommended & Easiest)
Run the following python command to automatically fix all primary key sequences in one go:

```bash
python manage.py shell -c "
from django.db import connection
from django.core.management.color import no_style
from django.apps import apps

sequence_sql = connection.ops.sequence_reset_sql(no_style(), apps.get_models())
with connection.cursor() as cursor:
    for sql in sequence_sql:
        cursor.execute(sql)
print('✅ All database primary key sequences have been successfully reset!')
"
```

### Option B: Generating SQL File
Alternatively, you can generate raw SQL commands for the primary apps and run them:
```bash
python manage.py sqlsequencereset questionbank community institutes messaging subscriptions > reset_sequences.sql
```
Then, execute the statements inside `reset_sequences.sql` on your PostgreSQL database using `psql` or your database admin manager (e.g., pgAdmin).

