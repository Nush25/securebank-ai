
from backend.app.core.supabase_client import get_supabase_client

try:
    supabase = get_supabase_client()

    response = supabase.table("conversations").select("id").limit(1).execute()

    print("SUPABASE CONNECTION SUCCESSFUL!")
    print("Conversations table is accessible.")

except Exception as error:
    print("SUPABASE CONNECTION FAILED:")
    print(error)
