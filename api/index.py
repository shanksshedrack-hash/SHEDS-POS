from server import app

# Vercel Python serverless function entry point
# Note: SQLite database will NOT persist on Vercel because the filesystem is ephemeral.
# For production, switch to PostgreSQL (e.g., Supabase, Neon, or Railway) and update DB_PATH.
def handler(request):
    return app
