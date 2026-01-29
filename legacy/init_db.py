import psycopg2
import sys

# Connection string provided by user
# Connection string provided by user
DB_URL = "postgresql://postgres.[YOUR-PROJECT-ID]:[YOUR-PASSWORD]@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres"

SQL_COMMANDS = [
    """
    -- Create items table
    CREATE TABLE IF NOT EXISTS public.items (
        id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
        created_at timestamptz DEFAULT now(),
        name text,
        image_path text,
        category text,
        tags text[],
        status text DEFAULT 'processing',
        ai_data jsonb
    );
    """,
    """
    -- Enable RLS
    ALTER TABLE public.items ENABLE ROW LEVEL SECURITY;
    """,
    """
    -- Create policies (Drop first to avoid errors if re-running)
    DROP POLICY IF EXISTS "Enable read access for all users" ON public.items;
    CREATE POLICY "Enable read access for all users" ON public.items FOR SELECT TO public USING (true);
    """,
    """
    DROP POLICY IF EXISTS "Enable insert access for all users" ON public.items;
    CREATE POLICY "Enable insert access for all users" ON public.items FOR INSERT TO public WITH CHECK (true);
    """,
    """
    DROP POLICY IF EXISTS "Enable update access for all users" ON public.items;
    CREATE POLICY "Enable update access for all users" ON public.items FOR UPDATE TO public USING (true);
    """,
    """
    -- Storage Bucket
    INSERT INTO storage.buckets (id, name, public) 
    VALUES ('wardrobe_images', 'wardrobe_images', true) 
    ON CONFLICT (id) DO NOTHING;
    """,
    """
    -- Storage Policies
    DROP POLICY IF EXISTS "Public Access" ON storage.objects;
    CREATE POLICY "Public Access" ON storage.objects FOR SELECT USING ( bucket_id = 'wardrobe_images' );
    """,
    """
    DROP POLICY IF EXISTS "Public Upload" ON storage.objects;
    CREATE POLICY "Public Upload" ON storage.objects FOR INSERT WITH CHECK ( bucket_id = 'wardrobe_images' );
    """
]

def init_db():
    print("Connecting to Supabase...")
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        print("Executing SQL commands...")
        for cmd in SQL_COMMANDS:
            try:
                cur.execute(cmd)
                print(f"Success: {cmd.strip().splitlines()[0]}")
            except Exception as e:
                print(f"Warning executing command: {e}")
                conn.rollback() # Rollback the failed command to continue
                continue
            conn.commit()
            
        cur.close()
        conn.close()
        print("Database initialization completed successfully!")
        
    except Exception as e:
        print(f"Critical Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
