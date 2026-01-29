# Supabase 設定指南

為了讓您的雲端衣櫃能正常運作，請依照以下步驟建立免費的 Supabase 專案。

## 步驟 1: 建立專案
1.  前往 [Supabase 官網](https://supabase.com/) 並登入 (可用 GitHub 帳號)。
2.  點擊 **"New Project"**。
3.  選擇一個 Organization (若無則建立一個)。
4.  填寫專案資訊：
    - **Name**: `WardrobeVCA` (或您喜歡的名字)
    - **Database Password**: 設定一個強密碼 (請記下來，雖然我們這次主要用 API Key)。PqrGA7Wh4Sdtd8pC
    - **Region**: 選擇離您最近的 (例如 `Northeast Asia (Tokyo)` 或 `Singapore`)。
5.  點擊 **"Create new project"**。等待幾分鐘讓資料庫初始化。

## 步驟 2: 取得 API Keys
專案建立完成後：
1.  前往 **Project Settings** (左下角齒輪圖示) -> **API**。
2.  找到 **Project URL**，複製下來 (例如 `https://xyz.supabase.co`)。
3.  找到 **Project API keys** -> **anon** (public)，複製下來。
    - *注意：不要使用 `service_role` key，那個權限太大，不適合放在網頁前端。*

**請將這兩組資料填入我們網頁版的「設定」頁面。**

## 步驟 3: 建立資料表 (Database)
1.  前往 **Table Editor** (左側選單表格圖示)。
2.  點擊 **"Create a new table"**。
3.  設定如下：
    - **Name**: `items`
    - **Enable Row Level Security (RLS)**: 勾選 (預設)。
    - **Columns**:
        - `id`: uuid, Primary Key, Default: `gen_random_uuid()`
        - `created_at`: timestamptz, Default: `now()`
        - `name`: text, Nullable
        - `image_path`: text, Nullable (存放 Storage 裡的路徑)
        - `category`: text, Nullable
        - `tags`: text[], Nullable (Array of text)
        - `status`: text, Default: `'processing'` (processing, available, laundry, etc.)
        - `ai_data`: jsonb, Nullable (存放 Gemini 分析的完整結果)
4.  點擊 **Save**。

## 步驟 4: 設定儲存空間 (Storage)
1.  前往 **Storage** (左側選單資料夾圖示)。
2.  點擊 **"New Bucket"**。
3.  設定如下：
    - **Name**: `wardrobe_images`
    - **Public bucket**: **開啟** (這樣才能讓 Gemini 讀取圖片，若要更安全需用 Signed URL，初期先開啟 Public 方便測試)。
4.  點擊 **Save**。

## 步驟 5: 設定存取權限 (RLS Policies)
為了讓網頁能讀寫資料，我們需要設定 RLS (Row Level Security)。

1.  前往 **SQL Editor** (左側選單 SQL 圖示)。
2.  貼上以下 SQL 語法並執行 (Run)：

```sql
-- 允許任何人讀取 items 表格 (唯讀)
create policy "Enable read access for all users"
on "public"."items"
as permissive
for select
to public
using (true);

-- 允許任何人新增資料 (為了測試方便，正式版建議加上 Auth)
create policy "Enable insert access for all users"
on "public"."items"
as permissive
for insert
to public
with check (true);

-- 允許任何人更新資料
create policy "Enable update access for all users"
on "public"."items"
as permissive
for update
to public
using (true);

-- 設定 Storage 權限 (允許上傳與讀取)
-- 注意：Supabase Storage 的 RLS 設定比較複雜，建議先在 Storage 介面設定 Policies
-- 或者執行以下 SQL (假設 bucket id 是 'wardrobe_images')
insert into storage.buckets (id, name, public)
values ('wardrobe_images', 'wardrobe_images', true)
on conflict (id) do nothing;

create policy "Public Access"
on storage.objects for select
using ( bucket_id = 'wardrobe_images' );

create policy "Public Upload"
on storage.objects for insert
with check ( bucket_id = 'wardrobe_images' );
```

完成以上步驟後，您的後端就準備好了！
