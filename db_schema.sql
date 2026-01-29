-- 1. Create items table
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

-- 2. Enable RLS
ALTER TABLE public.items ENABLE ROW LEVEL SECURITY;

-- 3. Create policies for items
-- Allow read access for all users
DROP POLICY IF EXISTS "Enable read access for all users" ON public.items;
CREATE POLICY "Enable read access for all users" ON public.items FOR SELECT TO public USING (true);

-- Allow insert access for all users
DROP POLICY IF EXISTS "Enable insert access for all users" ON public.items;
CREATE POLICY "Enable insert access for all users" ON public.items FOR INSERT TO public WITH CHECK (true);

-- Allow update access for all users
DROP POLICY IF EXISTS "Enable update access for all users" ON public.items;
CREATE POLICY "Enable update access for all users" ON public.items FOR UPDATE TO public USING (true);

-- 4. Create Storage Bucket
INSERT INTO storage.buckets (id, name, public) 
VALUES ('wardrobe_images', 'wardrobe_images', true) 
ON CONFLICT (id) DO NOTHING;

-- 5. Create policies for storage
-- Allow public access to images
DROP POLICY IF EXISTS "Public Access" ON storage.objects;
CREATE POLICY "Public Access" ON storage.objects FOR SELECT USING ( bucket_id = 'wardrobe_images' );

-- Allow public upload
DROP POLICY IF EXISTS "Public Upload" ON storage.objects;
CREATE POLICY "Public Upload" ON storage.objects FOR INSERT WITH CHECK ( bucket_id = 'wardrobe_images' );
