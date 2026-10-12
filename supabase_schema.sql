-- --------------------------------------------------------
-- Employee Registry Schema
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS public.employees (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    department TEXT NOT NULL,
    phone_number TEXT,
    email TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- RLS (Row Level Security) - optional but recommended
ALTER TABLE public.employees ENABLE ROW LEVEL SECURITY;

-- Allow read access for authenticated and anonymous users
CREATE POLICY "Allow read access on employees" 
ON public.employees 
FOR SELECT 
USING (true);

-- Allow insert/update/delete access for authenticated and anonymous users (or lock it down as needed)
CREATE POLICY "Allow full access on employees" 
ON public.employees 
FOR ALL 
USING (true);
