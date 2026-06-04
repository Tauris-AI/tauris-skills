# ARIES Reference Templates

This folder contains ARIES templates that should travel with the ARIES area when it is installed on its own.

## Files

- `aries_access_template.sqlite` - SQLite copy generated from the bundled ARIES Access template. It includes Access tables plus SQLite views for Access query/view objects.

The SQLite view objects are included for local inspection and agent workflows. When writing a working Access database, write into a copy of the Access template tables; the native Access queries/views remain in that Access template and will evaluate from the populated tables.
