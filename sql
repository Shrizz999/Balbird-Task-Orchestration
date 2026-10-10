-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.purchase_orders (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  po_number text NOT NULL,
  company_name text NOT NULL,
  order_date text,
  created_at timestamp with time zone NOT NULL DEFAULT timezone('utc'::text, now()),
  file_path text,
  CONSTRAINT purchase_orders_pkey PRIMARY KEY (id)
);
CREATE TABLE public.inventory (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  item_code text NOT NULL UNIQUE,
  description text,
  stock_qty integer NOT NULL DEFAULT 0,
  unit text NOT NULL DEFAULT 'PCS'::text,
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT inventory_pkey PRIMARY KEY (id)
);
CREATE TABLE public.part_vendors (
  id bigint NOT NULL DEFAULT nextval('part_vendors_id_seq'::regclass),
  part_code text NOT NULL,
  vendor_name text NOT NULL,
  vendor_type text NOT NULL DEFAULT 'local'::text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT part_vendors_pkey PRIMARY KEY (id)
);
CREATE TABLE public.tasks (
  task_id text NOT NULL,
  date text,
  description text,
  assigned_to text,
  assigned_by text,
  department text,
  deadline text,
  priority text,
  status text,
  reason text,
  source text,
  updated_by text,
  last_updated timestamp with time zone DEFAULT now(),
  checklist jsonb DEFAULT '[]'::jsonb,
  CONSTRAINT tasks_pkey PRIMARY KEY (task_id)
);
CREATE TABLE public.monthly_goals (
  goal_id text NOT NULL,
  time_frame text,
  week_month text,
  assigned_to text,
  given_by text,
  goal text,
  deadline text,
  status text,
  reason text,
  updated_by text,
  last_updated timestamp with time zone DEFAULT now(),
  checklist jsonb DEFAULT '[]'::jsonb,
  CONSTRAINT monthly_goals_pkey PRIMARY KEY (goal_id)
);
CREATE TABLE public.extension_requests (
  request_id uuid NOT NULL DEFAULT gen_random_uuid(),
  task_id text,
  task_description text,
  employee_name text,
  department text,
  current_deadline text,
  requested_deadline text,
  reason text,
  status text DEFAULT 'Pending'::text,
  manager_note text,
  manager_deadline text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT extension_requests_pkey PRIMARY KEY (request_id),
  CONSTRAINT extension_requests_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.tasks(task_id)
);
CREATE TABLE public.company_sops (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  department text,
  task_type text,
  content text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT company_sops_pkey PRIMARY KEY (id)
);