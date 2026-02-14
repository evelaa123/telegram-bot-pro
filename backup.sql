--
-- PostgreSQL database dump
--

\restrict qo2MMORZFc5JsCJw9e8he9VjddKJJKuj5SDPccda6hrveBjt7jrD6PF2D5M3rpg

-- Dumped from database version 15.15
-- Dumped by pg_dump version 15.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: adminrole; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.adminrole AS ENUM (
    'SUPERADMIN',
    'ADMIN',
    'VIEWER'
);


ALTER TYPE public.adminrole OWNER TO postgres;

--
-- Name: remindertype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.remindertype AS ENUM (
    'DIARY',
    'CHANNEL_EVENT',
    'ALARM'
);


ALTER TYPE public.remindertype OWNER TO postgres;

--
-- Name: requeststatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.requeststatus AS ENUM (
    'SUCCESS',
    'FAILED',
    'CANCELLED'
);


ALTER TYPE public.requeststatus OWNER TO postgres;

--
-- Name: requesttype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.requesttype AS ENUM (
    'TEXT',
    'IMAGE',
    'VIDEO',
    'VOICE',
    'DOCUMENT',
    'PRESENTATION',
    'text',
    'image',
    'video',
    'voice',
    'document',
    'presentation',
    'video_animate',
    'long_video',
    'VIDEO_ANIMATE',
    'LONG_VIDEO'
);


ALTER TYPE public.requesttype OWNER TO postgres;

--
-- Name: subscriptiontype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.subscriptiontype AS ENUM (
    'FREE',
    'PREMIUM',
    'premium',
    'free'
);


ALTER TYPE public.subscriptiontype OWNER TO postgres;

--
-- Name: videotaskstatus; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.videotaskstatus AS ENUM (
    'QUEUED',
    'IN_PROGRESS',
    'COMPLETED',
    'FAILED'
);


ALTER TYPE public.videotaskstatus OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: admins; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.admins (
    id integer NOT NULL,
    username character varying(100) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role public.adminrole NOT NULL,
    is_active boolean NOT NULL,
    last_login_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.admins OWNER TO postgres;

--
-- Name: admins_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.admins_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.admins_id_seq OWNER TO postgres;

--
-- Name: admins_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.admins_id_seq OWNED BY public.admins.id;


--
-- Name: api_usage_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.api_usage_logs (
    id integer NOT NULL,
    user_id integer,
    provider character varying(50) NOT NULL,
    model character varying(100) NOT NULL,
    endpoint character varying(100) NOT NULL,
    input_tokens integer,
    output_tokens integer,
    cost_usd numeric(10,6),
    cost_rub numeric(10,4),
    duration_ms integer,
    success boolean NOT NULL,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.api_usage_logs OWNER TO postgres;

--
-- Name: api_usage_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.api_usage_logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.api_usage_logs_id_seq OWNER TO postgres;

--
-- Name: api_usage_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.api_usage_logs_id_seq OWNED BY public.api_usage_logs.id;


--
-- Name: daily_limits; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.daily_limits (
    id integer NOT NULL,
    user_id integer NOT NULL,
    date date NOT NULL,
    text_count integer NOT NULL,
    image_count integer NOT NULL,
    video_count integer NOT NULL,
    voice_count integer NOT NULL,
    document_count integer NOT NULL,
    presentation_count integer NOT NULL,
    video_animate_count integer DEFAULT 0 NOT NULL,
    long_video_count integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.daily_limits OWNER TO postgres;

--
-- Name: daily_limits_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.daily_limits_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.daily_limits_id_seq OWNER TO postgres;

--
-- Name: daily_limits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.daily_limits_id_seq OWNED BY public.daily_limits.id;


--
-- Name: diary_entries; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.diary_entries (
    id integer NOT NULL,
    user_id integer NOT NULL,
    date date NOT NULL,
    title character varying(255),
    content text NOT NULL,
    tags json,
    mood integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.diary_entries OWNER TO postgres;

--
-- Name: diary_entries_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.diary_entries_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.diary_entries_id_seq OWNER TO postgres;

--
-- Name: diary_entries_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.diary_entries_id_seq OWNED BY public.diary_entries.id;


--
-- Name: reminders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reminders (
    id integer NOT NULL,
    user_id integer NOT NULL,
    type public.remindertype NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    remind_at timestamp with time zone NOT NULL,
    recurrence character varying(50),
    channel_message_id integer,
    channel_id bigint,
    is_active boolean NOT NULL,
    is_sent boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_triggered_at timestamp with time zone
);


ALTER TABLE public.reminders OWNER TO postgres;

--
-- Name: reminders_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.reminders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.reminders_id_seq OWNER TO postgres;

--
-- Name: reminders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.reminders_id_seq OWNED BY public.reminders.id;


--
-- Name: requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.requests (
    id integer NOT NULL,
    user_id integer NOT NULL,
    type public.requesttype NOT NULL,
    prompt text,
    response_preview character varying(500),
    tokens_input integer,
    tokens_output integer,
    cost_usd numeric(10,6),
    model character varying(50),
    status public.requeststatus NOT NULL,
    error_message text,
    duration_ms integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.requests OWNER TO postgres;

--
-- Name: requests_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.requests_id_seq OWNER TO postgres;

--
-- Name: requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.requests_id_seq OWNED BY public.requests.id;


--
-- Name: settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.settings (
    key character varying(100) NOT NULL,
    value json NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_by integer
);


ALTER TABLE public.settings OWNER TO postgres;

--
-- Name: subscriptions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.subscriptions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    payment_id character varying(255) NOT NULL,
    payment_provider character varying(50) NOT NULL,
    amount_rub numeric(10,2) NOT NULL,
    starts_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    is_active boolean NOT NULL,
    cancelled_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.subscriptions OWNER TO postgres;

--
-- Name: subscriptions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.subscriptions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.subscriptions_id_seq OWNER TO postgres;

--
-- Name: subscriptions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.subscriptions_id_seq OWNED BY public.subscriptions.id;


--
-- Name: support_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.support_messages (
    id integer NOT NULL,
    user_id integer NOT NULL,
    message text NOT NULL,
    is_from_user boolean NOT NULL,
    admin_id integer,
    is_read boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.support_messages OWNER TO postgres;

--
-- Name: support_messages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.support_messages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.support_messages_id_seq OWNER TO postgres;

--
-- Name: support_messages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.support_messages_id_seq OWNED BY public.support_messages.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    telegram_id bigint NOT NULL,
    username character varying(255),
    first_name character varying(255),
    last_name character varying(255),
    language_code character varying(10),
    is_blocked boolean NOT NULL,
    subscription_type public.subscriptiontype NOT NULL,
    subscription_expires_at timestamp with time zone,
    custom_limits json,
    settings json,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_active_at timestamp with time zone
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: video_tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.video_tasks (
    id integer NOT NULL,
    user_id integer NOT NULL,
    openai_video_id character varying(100),
    prompt text NOT NULL,
    model character varying(50) NOT NULL,
    status public.videotaskstatus NOT NULL,
    progress integer NOT NULL,
    result_file_id character varying(255),
    error_message text,
    chat_id bigint NOT NULL,
    message_id integer,
    duration_seconds integer NOT NULL,
    resolution character varying(20) NOT NULL,
    reference_image_file_id character varying(255),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    started_at timestamp with time zone,
    completed_at timestamp with time zone
);


ALTER TABLE public.video_tasks OWNER TO postgres;

--
-- Name: video_tasks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.video_tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.video_tasks_id_seq OWNER TO postgres;

--
-- Name: video_tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.video_tasks_id_seq OWNED BY public.video_tasks.id;


--
-- Name: admins id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admins ALTER COLUMN id SET DEFAULT nextval('public.admins_id_seq'::regclass);


--
-- Name: api_usage_logs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_usage_logs ALTER COLUMN id SET DEFAULT nextval('public.api_usage_logs_id_seq'::regclass);


--
-- Name: daily_limits id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.daily_limits ALTER COLUMN id SET DEFAULT nextval('public.daily_limits_id_seq'::regclass);


--
-- Name: diary_entries id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.diary_entries ALTER COLUMN id SET DEFAULT nextval('public.diary_entries_id_seq'::regclass);


--
-- Name: reminders id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reminders ALTER COLUMN id SET DEFAULT nextval('public.reminders_id_seq'::regclass);


--
-- Name: requests id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.requests ALTER COLUMN id SET DEFAULT nextval('public.requests_id_seq'::regclass);


--
-- Name: subscriptions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscriptions ALTER COLUMN id SET DEFAULT nextval('public.subscriptions_id_seq'::regclass);


--
-- Name: support_messages id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.support_messages ALTER COLUMN id SET DEFAULT nextval('public.support_messages_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: video_tasks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.video_tasks ALTER COLUMN id SET DEFAULT nextval('public.video_tasks_id_seq'::regclass);


--
-- Data for Name: admins; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.admins (id, username, password_hash, role, is_active, last_login_at, created_at) FROM stdin;
1	admin	$2b$12$GEDASwbrcN45zIhQH5CKQeLzHCz70isoxZe9WtWhig9BI3.12rXrq	SUPERADMIN	t	2026-02-05 03:23:54.288281+00	2026-02-05 01:07:05.246066+00
\.


--
-- Data for Name: api_usage_logs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.api_usage_logs (id, user_id, provider, model, endpoint, input_tokens, output_tokens, cost_usd, cost_rub, duration_ms, success, error_message, created_at) FROM stdin;
1	\N	cometapi	qwen-image	image	\N	\N	0.040000	\N	\N	t	\N	2026-02-05 04:35:08.010864+00
2	\N	cometapi	sora-2	video	\N	\N	0.200000	\N	\N	t	\N	2026-02-05 04:36:07.618058+00
3	\N	cometapi	whisper-1	audio	\N	\N	0.000112	\N	\N	t	\N	2026-02-05 04:43:17.528058+00
4	\N	cometapi	qwen3-max-2026-01-23	chat	53	1	0.000114	\N	\N	t	\N	2026-02-05 04:52:13.283987+00
5	\N	cometapi	qwen3-max-2026-01-23	chat	50	55	0.000540	\N	\N	t	\N	2026-02-05 04:52:16.526211+00
6	\N	cometapi	qwen-image	image	\N	\N	0.040000	\N	\N	t	\N	2026-02-05 04:53:38.452196+00
7	\N	cometapi	sora-2-all	video	\N	\N	\N	\N	\N	f	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 20260205132859798638387SIHCnxzJ)","type":"comet_api_error"}}	2026-02-05 05:29:01.190809+00
8	\N	cometapi	qwen3-max-2026-01-23	chat	1943	1077	0.012502	\N	\N	t	\N	2026-02-05 05:30:52.883946+00
9	\N	cometapi	sora-2-all	video	\N	\N	\N	\N	\N	f	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 2026020513313084131287jXTpB855)","type":"comet_api_error"}}	2026-02-05 05:31:31.47654+00
10	\N	cometapi	sora-2-all	video	\N	\N	\N	\N	\N	f	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 20260205133303693880863lP5cJdSq)","type":"comet_api_error"}}	2026-02-05 05:33:05.09152+00
11	\N	cometapi	sora-2	video	\N	\N	0.200000	\N	\N	t	\N	2026-02-05 06:13:15.089126+00
12	\N	cometapi	sora-2	video	\N	\N	0.200000	\N	\N	t	\N	2026-02-05 06:51:10.054218+00
13	\N	cometapi	whisper-1	audio	\N	\N	0.000056	\N	\N	t	\N	2026-02-05 06:59:08.183337+00
14	\N	cometapi	qwen3-max-2026-01-23	chat	1498	1567	0.015532	\N	\N	t	\N	2026-02-05 07:54:24.602547+00
15	\N	cometapi	qwen3-max-2026-01-23	chat	32	11	0.000152	\N	\N	t	\N	2026-02-05 07:55:19.895744+00
16	\N	cometapi	qwen3-max-2026-01-23	chat	1500	1118	0.011944	\N	\N	t	\N	2026-02-05 08:08:24.163492+00
17	\N	cometapi	dall-e-3	image	\N	\N	\N	\N	\N	f	Connection error.	2026-02-05 08:15:45.55933+00
18	\N	cometapi	dall-e-3	image	\N	\N	0.040000	\N	\N	t	\N	2026-02-05 08:17:14.484334+00
19	\N	cometapi	dall-e-3	image	\N	\N	0.040000	\N	\N	t	\N	2026-02-05 08:17:29.171053+00
20	\N	cometapi	dall-e-3	image	\N	\N	\N	\N	\N	f	Connection error.	2026-02-05 08:51:07.285576+00
21	\N	cometapi	dall-e-3	image	\N	\N	\N	\N	\N	f	Connection error.	2026-02-06 10:08:39.721345+00
22	\N	cometapi	dall-e-3	image	\N	\N	\N	\N	\N	f	Connection error.	2026-02-06 10:11:05.712134+00
23	\N	cometapi	sora-2	video	\N	\N	0.200000	\N	\N	t	\N	2026-02-06 14:53:17.86645+00
24	\N	cometapi	sora-2	video	\N	\N	0.200000	\N	\N	t	\N	2026-02-06 15:15:42.549887+00
25	\N	cometapi	whisper-1	audio	\N	\N	\N	\N	\N	f	Connection error.	2026-02-07 17:39:01.737283+00
26	\N	cometapi	sora-2	video	\N	\N	0.600000	\N	\N	t	\N	2026-02-07 17:55:27.545428+00
27	\N	cometapi	sora-2	video	\N	\N	0.600000	\N	\N	t	\N	2026-02-07 17:59:33.423466+00
28	\N	cometapi	sora-2	video	\N	\N	0.600000	\N	\N	t	\N	2026-02-07 18:03:20.633201+00
29	\N	cometapi	sora-2	video	\N	\N	0.600000	\N	\N	t	\N	2026-02-07 18:06:48.49937+00
30	\N	cometapi	qwen-image	image	\N	\N	\N	\N	\N	f	Request timed out.	2026-02-07 18:07:35.504361+00
31	\N	cometapi	qwen-image	image	\N	\N	0.040000	\N	\N	t	\N	2026-02-07 18:24:09.701703+00
32	\N	cometapi	sora-2	video	\N	\N	0.200000	\N	\N	t	\N	2026-02-07 18:26:59.703445+00
33	\N	cometapi	sora-2	video	\N	\N	0.600000	\N	\N	t	\N	2026-02-07 21:07:14.719205+00
34	\N	cometapi	sora-2	video	\N	\N	0.600000	\N	\N	t	\N	2026-02-07 21:10:49.431367+00
35	\N	cometapi	sora-2	video	\N	\N	0.600000	\N	\N	t	\N	2026-02-07 21:14:21.893204+00
36	\N	cometapi	sora-2	video	\N	\N	0.200000	\N	\N	t	\N	2026-02-07 22:44:03.160876+00
37	\N	cometapi	sora-2	video	\N	\N	0.200000	\N	\N	t	\N	2026-02-07 22:50:03.613364+00
38	\N	cometapi	sora-2	video	\N	\N	0.200000	\N	\N	t	\N	2026-02-07 22:59:49.742385+00
39	\N	cometapi	qwen3-max-2026-01-23	chat	157	111	0.001202	\N	\N	t	\N	2026-02-07 23:22:41.648748+00
40	\N	cometapi	sora-2-all	video	\N	\N	\N	\N	\N	f	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 202602080722448749252614W1Dwquh)","type":"comet_api_error"}}	2026-02-07 23:22:43.537758+00
41	\N	cometapi	qwen3-max-2026-01-23	chat	157	127	0.001330	\N	\N	t	\N	2026-02-07 23:23:53.059592+00
42	\N	cometapi	sora-2-all	video	\N	\N	\N	\N	\N	f	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 20260208072356156301933ZtXHp2s0)","type":"comet_api_error"}}	2026-02-07 23:23:54.818456+00
43	\N	cometapi	qwen3-max-2026-01-23	chat	144	122	0.001264	\N	\N	t	\N	2026-02-07 23:50:10.70321+00
44	\N	cometapi	sora-2	video	\N	\N	0.400000	\N	\N	t	\N	2026-02-07 23:50:14.996947+00
45	\N	cometapi	sora-2	video	\N	\N	0.200000	\N	\N	t	\N	2026-02-08 00:03:51.550481+00
46	\N	cometapi	sora-2	video	\N	\N	0.200000	\N	\N	t	\N	2026-02-08 00:06:39.398222+00
47	\N	cometapi	sora-2	video	\N	\N	0.600000	\N	\N	t	\N	2026-02-08 01:52:08.676906+00
48	\N	cometapi	sora-2	video	\N	\N	0.600000	\N	\N	t	\N	2026-02-08 01:55:39.881257+00
49	\N	cometapi	sora-2	video	\N	\N	\N	\N	\N	f	CometAPI video creation failed: 403 - {"code":null,"message":"user quota is not enough"}	2026-02-08 01:59:00.731353+00
50	\N	cometapi	sora-2	video	\N	\N	0.200000	\N	\N	t	\N	2026-02-08 03:34:14.717988+00
51	\N	cometapi	sora-2	video	\N	\N	0.600000	\N	\N	t	\N	2026-02-08 03:37:10.842308+00
52	\N	cometapi	sora-2	video	\N	\N	0.600000	\N	\N	t	\N	2026-02-08 03:40:45.336433+00
53	\N	cometapi	sora-2	video	\N	\N	0.600000	\N	\N	t	\N	2026-02-08 03:44:12.648913+00
54	\N	cometapi	qwen3-max-2026-01-23	chat	53	1	0.000114	\N	\N	t	\N	2026-02-08 03:52:46.815023+00
55	\N	cometapi	qwen3-max-2026-01-23	chat	50	13	0.000204	\N	\N	t	\N	2026-02-08 03:52:48.648027+00
56	\N	cometapi	qwen3-max-2026-01-23	chat	61	1	0.000130	\N	\N	t	\N	2026-02-08 03:53:02.399673+00
57	\N	cometapi	qwen-image	image	\N	\N	0.040000	\N	\N	t	\N	2026-02-08 03:53:08.549378+00
58	\N	cometapi	whisper-1	audio	\N	\N	\N	\N	\N	f	Connection error.	2026-02-09 12:39:13.754708+00
59	\N	cometapi	whisper-1	audio	\N	\N	0.001841	\N	\N	t	\N	2026-02-09 12:40:37.746397+00
60	\N	cometapi	whisper-1	audio	\N	\N	0.001423	\N	\N	t	\N	2026-02-09 12:40:40.518011+00
61	\N	cometapi	whisper-1	audio	\N	\N	0.000881	\N	\N	t	\N	2026-02-09 12:51:15.805842+00
62	\N	cometapi	whisper-1	audio	\N	\N	0.000839	\N	\N	t	\N	2026-02-09 12:51:18.995363+00
63	\N	cometapi	qwen3-max-2026-01-23	chat	54	1	0.000116	\N	\N	t	\N	2026-02-09 14:03:01.790312+00
64	\N	cometapi	qwen3-max-2026-01-23	chat	51	11	0.000190	\N	\N	t	\N	2026-02-09 14:03:03.563127+00
65	\N	cometapi	qwen-image	image	\N	\N	0.040000	\N	\N	t	\N	2026-02-09 14:13:06.50876+00
66	\N	cometapi	qwen-image	image	\N	\N	0.040000	\N	\N	t	\N	2026-02-09 14:13:49.181833+00
67	\N	cometapi	qwen3-max-2026-01-23	chat	54	1	0.000116	\N	\N	t	\N	2026-02-09 14:14:32.430201+00
68	\N	cometapi	qwen3-max-2026-01-23	chat	51	11	0.000190	\N	\N	t	\N	2026-02-09 14:14:34.038863+00
69	\N	cometapi	qwen3-max-2026-01-23	chat	52	57	0.000560	\N	\N	t	\N	2026-02-09 14:14:41.845978+00
70	\N	cometapi	qwen3-max-2026-01-23	chat	59	1	0.000126	\N	\N	t	\N	2026-02-09 14:14:58.854915+00
71	\N	cometapi	qwen3-max-2026-01-23	chat	56	105	0.000952	\N	\N	t	\N	2026-02-09 14:15:03.979745+00
72	\N	cometapi	qwen-image	image	\N	\N	0.040000	\N	\N	t	\N	2026-02-09 14:16:18.970307+00
73	\N	cometapi	qwen3-max-2026-01-23	chat	32	11	0.000152	\N	\N	t	\N	2026-02-12 22:09:26.197763+00
74	\N	cometapi	qwen-image	image	\N	\N	0.040000	\N	\N	t	\N	2026-02-12 23:31:36.371847+00
75	\N	cometapi	qwen3-max-2026-01-23	chat	67	1	0.000142	\N	\N	t	\N	2026-02-12 23:36:02.17357+00
76	\N	cometapi	qwen3-max-2026-01-23	chat	55	1	0.000118	\N	\N	t	\N	2026-02-12 23:37:15.117585+00
77	\N	cometapi	whisper-1	audio	\N	\N	0.000053	\N	\N	t	\N	2026-02-12 23:43:30.140622+00
78	\N	cometapi	qwen3-max-2026-01-23	chat	54	1	0.000116	\N	\N	t	\N	2026-02-12 23:47:01.867415+00
79	\N	cometapi	qwen3-max-2026-01-23	chat	59	1	0.000126	\N	\N	t	\N	2026-02-12 23:47:18.194239+00
80	\N	cometapi	qwen3-max-2026-01-23	chat	80	1	0.000168	\N	\N	t	\N	2026-02-12 23:47:59.826023+00
82	\N	cometapi	qwen3-max-2026-01-23	chat	42	1	0.000092	\N	\N	t	\N	2026-02-12 23:49:00.282626+00
81	\N	cometapi	qwen3-max-2026-01-23	chat	54	1	0.000116	\N	\N	t	\N	2026-02-12 23:48:30.50142+00
83	\N	cometapi	qwen3-max-2026-01-23	chat	63	1	0.000134	\N	\N	t	\N	2026-02-13 00:37:33.09414+00
84	\N	cometapi	qwen3-max-2026-01-23	chat	167	58	0.000798	\N	\N	t	\N	2026-02-13 00:45:19.227568+00
85	\N	cometapi	qwen3-max-2026-01-23	chat	31	40	0.000382	\N	\N	t	\N	2026-02-13 00:54:17.148349+00
86	\N	cometapi	qwen3-max-2026-01-23	chat	36	85	0.000752	\N	\N	t	\N	2026-02-13 00:54:21.77188+00
87	\N	cometapi	qwen3-max-2026-01-23	chat	39	52	0.000494	\N	\N	t	\N	2026-02-13 00:54:24.205644+00
88	\N	cometapi	qwen3-max-2026-01-23	chat	33	47	0.000442	\N	\N	t	\N	2026-02-13 00:55:42.607716+00
89	\N	cometapi	qwen3-max-2026-01-23	chat	40	91	0.000808	\N	\N	t	\N	2026-02-13 00:55:47.250933+00
90	\N	cometapi	qwen3-max-2026-01-23	chat	58	1	0.000124	\N	\N	t	\N	2026-02-13 00:58:28.524615+00
\.


--
-- Data for Name: daily_limits; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.daily_limits (id, user_id, date, text_count, image_count, video_count, voice_count, document_count, presentation_count, video_animate_count, long_video_count) FROM stdin;
15	2	2026-02-05	1	1	0	0	0	0	0	0
1	1	2026-02-05	13	1	1	4	8	2	0	0
32	1	2026-02-06	0	0	2	0	0	0	0	0
38	1	2026-02-07	2	9	1	0	0	0	3	2
55	1	2026-02-08	1	3	1	0	0	0	1	1
62	2	2026-02-08	1	1	0	0	0	0	0	0
64	1	2026-02-09	0	0	0	4	0	0	0	0
68	3	2026-02-09	6	3	0	0	0	0	0	0
77	1	2026-02-12	1	0	0	0	0	0	0	0
78	3	2026-02-12	6	1	0	1	0	1	0	0
87	3	2026-02-13	0	0	0	0	2	0	0	0
\.


--
-- Data for Name: diary_entries; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.diary_entries (id, user_id, date, title, content, tags, mood, created_at, updated_at) FROM stdin;
1	1	2026-02-05	\N	g	\N	\N	2026-02-05 01:38:59.690898+00	2026-02-05 01:38:59.690898+00
\.


--
-- Data for Name: reminders; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.reminders (id, user_id, type, title, description, remind_at, recurrence, channel_message_id, channel_id, is_active, is_sent, created_at, last_triggered_at) FROM stdin;
3	1	ALARM	╨С╤Г╨┤╨╕╨╗╤М╨╜╨╕╨║ ╨╜╨░ 07:39	\N	2026-02-13 07:39:00+00	daily	\N	\N	t	f	2026-02-05 04:37:31.664042+00	2026-02-12 21:51:00.382871+00
4	1	ALARM	╨С╤Г╨┤╨╕╨╗╤М╨╜╨╕╨║ ╨╜╨░ 09:58	\N	2026-02-13 09:58:00+00	daily	\N	\N	t	f	2026-02-05 06:56:44.495439+00	2026-02-12 21:51:00.382871+00
5	1	ALARM	╨С╤Г╨┤╨╕╨╗╤М╨╜╨╕╨║ ╨╜╨░ 10:28	\N	2026-02-13 10:28:00+00	daily	\N	\N	t	f	2026-02-05 07:26:56.277813+00	2026-02-12 21:51:00.382871+00
6	1	ALARM	╨С╤Г╨┤╨╕╨╗╤М╨╜╨╕╨║ ╨╜╨░ 11:49	\N	2026-02-13 11:49:00+00	daily	\N	\N	t	f	2026-02-05 07:48:28.76495+00	2026-02-12 21:51:00.382871+00
7	1	ALARM	╨С╤Г╨┤╨╕╨╗╤М╨╜╨╕╨║ ╨╜╨░ 5:14	\N	2026-02-13 02:14:00+00	daily	\N	\N	t	f	2026-02-07 02:12:29.958977+00	2026-02-12 21:51:00.382871+00
1	1	ALARM	╨С╤Г╨┤╨╕╨╗╤М╨╜╨╕╨║ ╨╜╨░ 4:13	\N	2026-02-13 04:13:00+00	daily	\N	\N	t	f	2026-02-05 01:12:31.152274+00	2026-02-12 21:51:00.382871+00
2	1	ALARM	╨С╤Г╨┤╨╕╨╗╤М╨╜╨╕╨║ ╨╜╨░ 07:00	\N	2026-02-13 07:00:00+00	daily	\N	\N	t	f	2026-02-05 03:58:43.278322+00	2026-02-12 21:51:00.382871+00
\.


--
-- Data for Name: requests; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.requests (id, user_id, type, prompt, response_preview, tokens_input, tokens_output, cost_usd, model, status, error_message, duration_ms, created_at) FROM stdin;
1	1	TEXT	q	\N	\N	\N	\N	gpt-4o-mini	FAILED	Error code: 403 - {'error': {'code': 'unsupported_country_region_territory', 'message': 'Country, region, or territory not supported', 'param': None, 'type': 'request_forbidden'}}	347	2026-02-05 01:11:23.293748+00
2	1	TEXT	q	\N	\N	\N	\N	gpt-4o-mini	FAILED	Error code: 403 - {'error': {'code': 'unsupported_country_region_territory', 'message': 'Country, region, or territory not supported', 'param': None, 'type': 'request_forbidden'}}	153	2026-02-05 01:14:04.040395+00
3	1	VOICE	\N	\N	\N	\N	\N	unknown	FAILED	Error code: 403 - {'error': {'code': 'unsupported_country_region_territory', 'message': 'Country, region, or territory not supported', 'param': None, 'type': 'request_forbidden'}}	\N	2026-02-05 01:14:08.543788+00
4	1	TEXT	ЁЯУК ╨Ы╨╕╨╝╨╕╤В╤Л	\N	\N	\N	\N	gpt-4o-mini	FAILED	Error code: 403 - {'error': {'code': 'unsupported_country_region_territory', 'message': 'Country, region, or territory not supported', 'param': None, 'type': 'request_forbidden'}}	92	2026-02-05 01:14:50.434634+00
5	1	TEXT	ЁЯУК ╨Ы╨╕╨╝╨╕╤В╤Л	\N	\N	\N	\N	gpt-4o-mini	FAILED	Error code: 403 - {'error': {'code': 'unsupported_country_region_territory', 'message': 'Country, region, or territory not supported', 'param': None, 'type': 'request_forbidden'}}	104	2026-02-05 01:15:24.967495+00
6	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	\N	\N	\N	\N	gpt-4o-mini	FAILED	Error code: 403 - {'error': {'code': 'unsupported_country_region_territory', 'message': 'Country, region, or territory not supported', 'param': None, 'type': 'request_forbidden'}}	155	2026-02-05 01:15:58.337876+00
7	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	\N	\N	\N	\N	gpt-4o-mini	FAILED	Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-your-**********-key. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}	950	2026-02-05 01:16:23.936281+00
8	1	TEXT	Themikeone ╨┐╨╛╨╖╨▓╨░╨╗ ╨╡╨╝╤Г ╨▓╨╕╨┤╨╛╤Б ╨╖╨░╨┐╨╕╤Б╨░╤В╤М ╨╕ ╨▓╨╛╤В ╤В╨╛╨╗╤М╨║╨╛ ╨╜╨╡╨┤╨░╨▓╨╜╨╛ ╨╖╨░╨║╨╛╨╜╤З╨╕╨╗╨╕. ╨п ╤В╨░╨║ ╨╡╤Й╨╡ ╨╜╨╕╨║╨╛╨│╨┤╨░ ╨╜╨╡ ╤А╨╢╨░╨╗)) ╨╢╨┤╨╕╤В╨╡, ╨╜╨╡╨┤╨╡╨╗╨╕ ╤З╨╡╤А╨╡╨╖ 2-3 ╤Г ╨╜╨╡╨│╨╛ ╨╜╨░ ╨║╨░╨╜╨░╨╗╨╡. ╨Ы╨╡╤Е╨░ ╨┐╨╕╨╖╨┤╨╡╤Ж ╤А╨╡╤Б╨┐╨╡╨║╤В╨╛╨▓╤Л╨╣ ╤З╤Г╨▓╨░╨║. ╨в╨░╨║ ╨╖╨░╨╝╨╛╤А╨╛╤З╨╕╤В╤М╤Б╤П ╨╜╨░╨┤ ╨║╨╛╨╜╤В╨╡╨╜╤В╨╛╨╝, ╤Н╤В╨╛ ╨┐╤А╨╛╤Б╤В╨╛ ╨╢╨╡╤Б╤В╤М) \n\n╨Э╨░╤Б╤З╨╡╤В ╨╜╨╛╤З╨╜╨╛╨│╨╛ ╤Б╤В╤А╨╕╨╝╨░ ╤Е╨╖╤Е╨╖╤Е╨╖ ╨Т╨░╨╝ ╨╜╨░╨┤╨╛ ?	\N	\N	\N	\N	gpt-4o-mini	FAILED	Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-your-**********-key. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}	638	2026-02-05 01:39:21.896497+00
9	1	TEXT	123	\N	\N	\N	\N	gpt-4o-mini	FAILED	Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-your-**********-key. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}	1264	2026-02-05 02:10:27.372528+00
10	1	TEXT	╨┐╤А╨▓╨╕╨╡╤В	\N	\N	\N	\N	gpt-4o-mini	FAILED	Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-your-**********-key. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}	791	2026-02-05 02:12:53.537346+00
11	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В\\	\N	\N	\N	\N	gpt-4o-mini	FAILED	Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-your-**********-key. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}	758	2026-02-05 02:13:01.553288+00
12	1	VIDEO	╨║╨╛╤В	\N	\N	\N	\N	sora-2	FAILED	Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-your-**********-key. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}	\N	2026-02-05 02:16:29.794419+00
13	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	\N	\N	\N	\N	qwen-3-max	FAILED	AIService.generate_text_stream() got an unexpected keyword argument 'provider'	0	2026-02-05 02:43:17.749216+00
14	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	\N	\N	\N	\N	qwen-3-max	FAILED	AIService.generate_text_stream() got an unexpected keyword argument 'provider'	0	2026-02-05 02:43:39.674056+00
15	1	TEXT	╨┐╤А╨╕╨▓╤В	\N	\N	\N	\N	qwen-3-max	FAILED	Error code: 503 - {'error': {'code': 'model_not_found', 'message': 'no available channel for group default and model qwen-3-max (distributor) (request id: 2026020510475766344672w8Jkt8U8)', 'type': 'comet_api_error'}}	5002	2026-02-05 02:47:57.031725+00
16	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	\N	\N	\N	\N	qwen-3-max	FAILED	Error code: 503 - {'error': {'code': 'model_not_found', 'message': 'no available channel for group default and model qwen-3-max (distributor) (request id: 202602051049039738343066ifI2TMp)', 'type': 'comet_api_error'}}	4581	2026-02-05 02:49:03.899612+00
17	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	\N	\N	\N	\N	qwen-3-max	FAILED	Error code: 503 - {'error': {'code': 'model_not_found', 'message': 'no available channel for group default and model qwen-3-max (distributor) (request id: 20260205105147610494413fi8qd7Hu)', 'type': 'comet_api_error'}}	5026	2026-02-05 02:51:47.674205+00
18	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	\N	\N	\N	\N	qwen-3-max	FAILED	Error code: 503 - {'error': {'code': 'model_not_found', 'message': 'no available channel for group default and model qwen-3-max (distributor) (request id: 20260205105749791849450gqkbqMGC)', 'type': 'comet_api_error'}}	5414	2026-02-05 02:57:49.880118+00
19	1	VOICE	\N	╨а╨╡╨┤╨░╨║╤В╨╛╤А ╤Б╤Г╨▒╤В╨╕╤В╤А╨╛╨▓ ╨Р.╨б╨╡╨╝╨║╨╕╨╜ ╨Ъ╨╛╤А╤А╨╡╨║╤В╨╛╤А ╨Р.╨Х╨│╨╛╤А╨╛╨▓╨░	\N	\N	0.000051	whisper-1	SUCCESS	\N	\N	2026-02-05 03:02:10.804737+00
20	1	VOICE	\N	╨Я╤А╨╕╨▓╨╡╤В!	\N	\N	0.000053	whisper-1	SUCCESS	\N	\N	2026-02-05 03:02:26.820162+00
21	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	\N	\N	\N	\N	qwen-3-max	FAILED	Error code: 503 - {'error': {'code': 'model_not_found', 'message': 'no available channel for group default and model qwen-3-max (distributor) (request id: 20260205113300976347818SjP5xGDt)', 'type': 'comet_api_error'}}	4823	2026-02-05 03:33:01.117489+00
22	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	\N	\N	\N	\N	qwen-3-max	FAILED	Error code: 503 - {'error': {'code': 'model_not_found', 'message': 'no available channel for group default and model qwen-3-max (distributor) (request id: 20260205113334212550640qoBKxlS8)', 'type': 'comet_api_error'}}	4726	2026-02-05 03:33:34.285331+00
23	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	╨Я╤А╨╕╨▓╨╡╤В! ╨з╨╡╨╝ ╨╝╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М? ЁЯШК	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	4512	2026-02-05 03:35:37.24225+00
24	1	TEXT	╤З╤В╨╛ ╤П ╤В╨╛╨╗╤М╨║╨╛ ╤З╤В╨╛ ╤В╨╡╨▒╨╡ ╨┐╨╕╤Б╨░╨╗	╨в╤Л ╤В╨╛╨╗╤М╨║╨╛ ╤З╤В╨╛ ╨╜╨░╨┐╨╕╤Б╨░╨╗: **┬л╨┐╤А╨╕╨▓╨╡╤В┬╗** ЁЯШК  \n╨е╨╛╤З╨╡╤И╤М ╨┐╤А╨╛╨┤╨╛╨╗╨╢╨╕╤В╤М ╤А╨░╨╖╨│╨╛╨▓╨╛╤А ╨╕╨╗╨╕ ╤Г ╤В╨╡╨▒╤П ╨╡╤Б╤В╤М ╨║╨░╨║╨╛╨╣-╤В╨╛ ╨▓╨╛╨┐╤А╨╛╤Б?	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	3601	2026-02-05 03:36:08.503829+00
25	1	IMAGE	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	\N	\N	\N	\N	unknown	FAILED	object of type 'NoneType' has no len()	\N	2026-02-05 03:36:30.883311+00
26	1	VIDEO	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	\N	\N	\N	\N	sora-2	FAILED	Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-your-**********-key. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}	\N	2026-02-05 03:36:49.950921+00
27	1	IMAGE	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	\N	\N	\N	\N	unknown	FAILED	object of type 'NoneType' has no len()	\N	2026-02-05 03:37:25.079127+00
28	1	IMAGE	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	\N	\N	\N	\N	unknown	FAILED	object of type 'NoneType' has no len()	\N	2026-02-05 03:38:12.28305+00
29	1	IMAGE	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	\N	\N	\N	\N	unknown	FAILED	object of type 'NoneType' has no len()	\N	2026-02-05 03:44:11.077082+00
30	1	IMAGE	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	\N	\N	\N	\N	unknown	FAILED	object of type 'NoneType' has no len()	\N	2026-02-05 03:46:06.741906+00
31	1	IMAGE	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	\N	\N	\N	\N	unknown	FAILED	object of type 'NoneType' has no len()	\N	2026-02-05 03:46:30.854669+00
32	1	IMAGE	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	\N	\N	\N	\N	unknown	FAILED	object of type 'NoneType' has no len()	\N	2026-02-05 03:48:11.920487+00
33	1	IMAGE	╨║╨░╨║╨░╤П ╤В╤Л ╨╝╨╛╨┤╨╡╨╗╤М	\N	\N	\N	\N	unknown	FAILED	object of type 'NoneType' has no len()	\N	2026-02-05 03:50:35.702402+00
34	1	TEXT	╨║╨░╨║╨░╤П ╤В╤Л ╨╝╨╛╨┤╨╡╨╗╤М	╨п тАФ **Qwen**, ╤Б╨▓╨╡╤А╤Е╨╝╨░╤Б╤И╤В╨░╨▒╨╜╨░╤П ╤П╨╖╤Л╨║╨╛╨▓╨░╤П ╨╝╨╛╨┤╨╡╨╗╤М, ╤А╨░╨╖╤А╨░╨▒╨╛╤В╨░╨╜╨╜╨░╤П Alibaba Cloud. ╨Ь╨╡╨╜╤П ╤В╨░╨║╨╢╨╡ ╨╜╨░╨╖╤Л╨▓╨░╤О╤В **Tongyi Qianwen**.  \n╨п ╤Г╨╝╨╡╤О ╨╛╤В╨▓╨╡╤З╨░╤В╤М ╨╜╨░ ╨▓╨╛╨┐╤А╨╛╤Б╤Л, ╨┐╨╕╤Б╨░╤В╤М ╤В╨╡╨║╤Б╤В╤Л, ╨┐╤А╨╛╨│╤А╨░╨╝╨╝╨╕╤А╨╛╨▓╨░╤В╤М, ╤А╨░╤Б╤Б╤Г╨╢╨┤╨░╤В╤М, ╨╕╨│╤А╨░╤В╤М ╨▓ ╨╕╨│╤А╤Л ╨╕ ╨╝╨╜╨╛╨│╨╛╨╡ ╨┤╤А╤Г╨│╨╛╨╡.  \n╨Х╤Б╨╗╨╕ ╤Г ╤В╨╡╨▒╤П ╨╡╤Б╤В╤М ╨╗╤О╨▒╨╛╨╣ ╨▓╨╛╨┐╤А╨╛╤Б ╨╕╨╗╨╕ ╨╖╨░╨┤╨░╤З╨░ тАФ ╨┐╤А╨╛╤Б╤В╨╛ ╤Б╨║╨░╨╢╨╕! ЁЯШК	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	6315	2026-02-05 03:50:54.377051+00
35	1	TEXT	ЁЯУК ╨Ы╨╕╨╝╨╕╤В╤Л	╨Т╨╛╤В ╨╛╤Б╨╜╨╛╨▓╨╜╤Л╨╡ **╨╗╨╕╨╝╨╕╤В╤Л Qwen (Tongyi Qianwen)**, ╨░╨║╤В╤Г╨░╨╗╤М╨╜╤Л╨╡ ╨╜╨░ 2024тАУ2025 ╨│╨╛╨┤:\n\n### ЁЯФ╣ **╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В╨╜╨╛╨╡ ╨╛╨║╨╜╨╛**\n- **╨Ь╨░╨║╤Б╨╕╨╝╨░╨╗╤М╨╜╨░╤П ╨┤╨╗╨╕╨╜╨░ ╨║╨╛╨╜╤В╨╡╨║╤Б╤В╨░**: ╨┤╨╛ **32 768 ╤В╨╛╨║╨╡╨╜╨╛╨▓** (╨▓ ╨╖╨░╨▓╨╕╤Б╨╕╨╝╨╛╤Б╤В╨╕ ╨╛╤В ╨▓╨╡╤А╤Б╨╕╨╕).\n- **╨Ь╨░╨║╤Б╨╕╨╝╨░╨╗╤М╨╜╨░╤П ╨┤╨╗╨╕╨╜╨░ ╨│╨╡╨╜╨╡╤А╨░╤Ж╨╕╨╕**: ╨╛╨▒╤Л╤З╨╜╨╛ ╨┤╨╛ **8192 ╤В╨╛╨║╨╡╨╜╨╛╨▓** ╨╖╨░ ╨╛╨┤╨╕╨╜ ╨╖╨░╨┐╤А╨╛╤Б.\n\n### ЁЯФ╣ **╨Т╨╡╤А╤Б╨╕╨╕ ╨╝╨╛╨┤╨╡╨╗╨╕**\n- **Qwen-Max** тАФ ╤Б╨░╨╝╨░╤П ╨╝╨╛╤Й╨╜╨░╤П, ╨┐╨╛╨┤╤Е╨╛╨┤╨╕╤В ╨┤╨╗╤П ╤Б╨╗╨╛╨╢╨╜╤Л╤Е ╨╖╨░╨┤╨░╤З, ╨╜╨╛ ╨┤╨╛╤А╨╛╨╢╨╡ ╨╕ ╨╝╨╡╨┤╨╗╨╡╨╜╨╜╨╡╨╡.\n- **Qwen-Plus** тАФ ╨▒╨░╨╗╨░╨╜╤Б ╨╝╨╡╨╢╨┤╤Г ╤Б╨║╨╛╤А╨╛╤Б╤В╤М╤О, ╤Б╤В╨╛╨╕╨╝╨╛╤Б╤В╤М╤О ╨╕ ╨║╨░╤З╨╡╤Б╤В╨▓╨╛╨╝.\n- **Qwen-Turbo** тАФ ╨▒╤Л╤Б╤В╤А╨░╤П ╨╕ ╨┤╨╡╤И╤С╨▓╨░╤П, ╨┐╨╛╨┤╤Е╨╛╨┤╨╕╤В ╨┤╨╗╤П ╨┐╤А╨╛╤Б╤В╤Л╤Е 	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	16809	2026-02-05 03:54:33.466804+00
36	1	VIDEO	╨║╨╛╤В ╨╕╨│╤А╨░╨╡╤В ╨╜╨░ ╨┐╨╕╨░╨╜╨╕╨╜╨╛	\N	\N	\N	\N	sora-2	FAILED	Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-your-**********-key. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}	\N	2026-02-05 03:55:16.627938+00
37	1	IMAGE	╨║╨╛╤В ╨║╨╛╤Б╨╝╨╛╨╜╨░╨▓╤В	\N	\N	\N	\N	unknown	FAILED	object of type 'NoneType' has no len()	\N	2026-02-05 04:23:39.012253+00
38	1	IMAGE	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	\N	\N	\N	0.040000	qwen-image	SUCCESS	\N	\N	2026-02-05 04:35:11.971116+00
39	1	DOCUMENT	╤Б╤Г╨╝╨╝╨░╤А╨╕╨╖╨╕╤А╤Г╨╣	\N	\N	\N	\N	gpt-4o	FAILED	Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-your-**********-key. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}	\N	2026-02-05 04:35:47.870195+00
40	1	VIDEO	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡ ╤Е╨╛╨┤╨╕╤В ╨▓ ╤Б╨║╨░╤Д╨░╨╜╨┤╤А╨╡	\N	\N	\N	\N	sora-2	FAILED	object bytes can't be used in 'await' expression	\N	2026-02-05 04:38:37.555898+00
41	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	╨Я╤А╨╕╨▓╨╡╤В! ╨з╨╡╨╝ ╨╝╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М? ЁЯШК	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	2833	2026-02-05 04:40:35.171796+00
42	1	TEXT	╤Б╨┤╨╡╨╗╨░╨╣ ╨║╤А╤Г╤В╨╛╨╡ ╤В╨│ ╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╨╡ ╤Б ╤Д╨╛╤А╨╝╨░╤В╨╕╤А╨╛╨▓╨░╨╜╨╕╨╡╨╝	╨Ъ╨╛╨╜╨╡╤З╨╜╨╛! ╨Т╨╛╤В ╨┐╤А╨╕╨╝╨╡╤А **╨║╤А╤Г╤В╨╛╨│╨╛ Telegram-╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╤П** ╤Б ╨╕╤Б╨┐╨╛╨╗╤М╨╖╨╛╨▓╨░╨╜╨╕╨╡╨╝ ╤Д╨╛╤А╨╝╨░╤В╨╕╤А╨╛╨▓╨░╨╜╨╕╤П:\n\n---\n\nЁЯФе **╨Т╨Э╨Ш╨Ь╨Р╨Э╨Ш╨Х! ╨Т╨Р╨Ц╨Э╨Р╨п ╨Ш╨Э╨д╨Ю╨а╨Ь╨Р╨ж╨Ш╨п** ЁЯФе\n\n╨Я╤А╨╕╨▓╨╡╤В, ╨║╨╛╨╝╨░╨╜╨┤╨░! ЁЯЪА  \n╨б╨╡╨│╨╛╨┤╨╜╤П ╨╝╤Л ╨╖╨░╨┐╤Г╤Б╨║╨░╨╡╨╝ **╨╜╨╛╨▓╤Л╨╣ ╤Н╤В╨░╨┐ ╨┐╤А╨╛╨╡╨║╤В╨░** тАФ ╨╕ ╤Н╤В╨╛ ╨▒╤Г╨┤╨╡╤В ЁЯФе!\n\nЁЯУМ **╨з╤В╨╛ ╨╜╤Г╨╢╨╜╨╛ ╤Б╨┤╨╡╨╗╨░╤В╤М:**  \nтЬЕ ╨Ч╨░╨▓╨╡╤А╤И╨╕╤В╤М ╨╖╨░╨┤╨░╤З╨╕ ╨┤╨╛ **18:00**  \nтЬЕ ╨Я╤А╨╕╤Б╨╗╨░╤В╤М ╨╛╤В╤З╤С╤В╤Л ╨▓ ╨║╨░╨╜╨░╨╗ **#╨╛╤В╤З╤С╤В╤Л**  \nтЬЕ ╨Э╨╡ ╨╖╨░╨▒╤Л╤В╤М ╨┐╤А╨╛ ╨┤╨╡╨┤╨╗╨░╨╣╨╜ тАФ **╨╖╨░╨▓╤В╤А╨░ ╨▓ 10:00**!\n\nЁЯТм ╨Т╨╛╨┐╤А╨╛╤Б╤Л? ╨Я╨╕╤И╨╕ ╤Б╤О╨┤╨░ тАФ ╨╛╨┐╨╡╤А╨░╤В╨╕╨▓╨╜╨╛ ╨╛╤В╨▓╨╡╤З╤Г!  \nЁЯОп ╨г╨▓╨╡╤А╨╡╨╜, ╤Г ╨╜╨░╤Б ╨▓╤Б╤С ╨┐╨╛╨╗╤Г╤З╨╕╤В╤Б╤П тАФ ╨▓╨╝╨╡╤Б╤В╨╡ ╨╝╤Л ╤Б╨╕╨╗╨░! ЁЯТк\n\n---\n\n╨е╨╛╤З╨╡╤И╤М ╨┐╨╛╨┤ ╨║╨╛╨╜╨║╤А╨╡╤В╨╜╤Г╤О ╤В╨╡╨╝╤Г (╨░╨╜╨╛╨╜╤Б, ╨╜╨░╨┐╨╛╨╝╨╕╨╜	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	8418	2026-02-05 04:42:26.802108+00
43	1	VOICE	\N	╨Ъ╨░╨║╨░╤П ╤Ж╨╡╨╜╨░ ╨╜╨░ ╤Е╨╗╨╡╨▒?	\N	\N	0.000112	whisper-1	SUCCESS	\N	\N	2026-02-05 04:43:17.632995+00
44	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	╨Я╤А╨╕╨▓╨╡╤В! ЁЯШК  \n╨з╨╡╨╝ ╨╝╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М?	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	3676	2026-02-05 04:48:32.615716+00
45	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	╨Я╤А╨╕╨▓╨╡╤В-╨┐╤А╨╕╨▓╨╡╤В! ЁЯШД  \n╨У╨╛╤В╨╛╨▓ ╨┐╨╛╨╝╨╛╤З╤М тАФ ╨┐╤А╨╛╤Б╤В╨╛ ╤Б╨║╨░╨╢╨╕, ╤З╤В╨╛ ╨╜╤Г╨╢╨╜╨╛!	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	3484	2026-02-05 04:49:15.579555+00
46	1	TEXT	╨┐╤А╨╕╨▓╨╡╤В	╨Я╤А╨╕╨▓╨╡╤В! ╨в╤Л ╤Г╨╢╨╡ ╤В╤А╨╡╤В╨╕╨╣ ╤А╨░╨╖ ╨╖╨░╤Е╨╛╨┤╨╕╤И╤М тАФ ╨▓╨╕╨┤╨╕╨╝╨╛, ╤З╤В╨╛-╤В╨╛ ╨▓╨░╨╢╨╜╨╛╨╡ ╨╖╨░╨┤╤Г╨╝╨░╨╗ ЁЯШП  \n╨У╨╛╨▓╨╛╤А╨╕, ╤П ╨╜╨░ ╤Б╨▓╤П╨╖╨╕! ЁЯТм	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	4479	2026-02-05 04:49:21.685472+00
47	2	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╤Ж\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╨┐╤А╨╕╨▓╨╡╤В	╨Я╤А╨╕╨▓╨╡╤В! ╨Я╨╛╤Е╨╛╨╢╨╡, ╨▓╨░╤И╨╡ ╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╨╡ ╨╛╨▒╤А╤Л╨▓╨░╨╡╤В╤Б╤П ╨╜╨░ ┬л╤Ж┬╗ тАФ ╨▓╨╛╨╖╨╝╨╛╨╢╨╜╨╛, ╨▓╤Л ╤Е╨╛╤В╨╡╨╗╨╕ ╤З╤В╨╛-╤В╨╛ ╤Г╤В╨╛╤З╨╜╨╕╤В╤М ╨╕╨╗╨╕ ╤Б╨┐╤А╨╛╤Б╨╕╤В╤М? ╨Э╨░╨┐╨╕╤И╨╕╤В╨╡ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╡╨╡, ╨╕ ╤П ╨┐╨╛╤Б╤В╨░╤А╨░╤О╤Б╤М ╨┐╨╛╨╝╨╛╤З╤М!	\N	\N	0.000540	qwen3-max-2026-01-23	SUCCESS	\N	\N	2026-02-05 04:52:16.665187+00
48	2	IMAGE	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╤Ж\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╤Д╨╛╤В╨╛ ╤Г╨╖╨▒╨╡╨║╨░	\N	\N	\N	0.040000	dall-e-3	SUCCESS	\N	\N	2026-02-05 04:53:43.014798+00
49	1	VIDEO	╨║╨╛╤В ╨╕╨│╤А╨░╨╡╤В ╨╜╨░ ╨┐╨╕╨░╨╜╨╕╨╜╨╛ ╨▓ ╨┤╨╢╨░╨╖╨╛╨▓╨╛╨╝ ╨║╨╗╤Г╨▒╨╡, ╨╜╤Г╨░╤А ╤Б╤В╨╕╨╗╤М	\N	\N	\N	\N	sora-2-all	FAILED	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 20260205132859798638387SIHCnxzJ)","type":"comet_api_error"}}	\N	2026-02-05 05:29:01.976183+00
50	1	DOCUMENT	╨б╤Г╨╝╨╝╨░╤А╨╕╨╖╨╕╤А╤Г╨╣ ╤Н╤В╨╛╤В ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В. ╨Т╤Л╨┤╨╡╨╗╨╕ ╨║╨╗╤О╤З╨╡╨▓╤Л╨╡ ╨┐╤Г╨╜╨║╤В╤Л ╨╕ ╨│╨╗╨░╨▓╨╜╤Л╨╡ ╨▓╤Л╨▓╨╛╨┤╤Л.	╨Т╨╛╤В ╨║╤А╨░╤В╨║╨╛╨╡ ╤А╨╡╨╖╤О╨╝╨╡ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В╨░ ╤Б ╨▓╤Л╨┤╨╡╨╗╨╡╨╜╨╕╨╡╨╝ ╨║╨╗╤О╤З╨╡╨▓╤Л╤Е ╨┐╤Г╨╜╨║╤В╨╛╨▓ ╨╕ ╨│╨╗╨░╨▓╨╜╤Л╤Е ╨▓╤Л╨▓╨╛╨┤╨╛╨▓:\n\n---\n\n### **╨Ю╨▒╤Й╨░╤П ╨╕╨╜╤Д╨╛╤А╨╝╨░╤Ж╨╕╤П ╨╛╨▒ ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╨╡**  \n- **╨Ь╨░╤А╨║╨░**: Audi  \n- **╨в╨╕╨┐ ╨┤╨▓╨╕╨│╨░╤В╨╡╨╗╤П**: ╨С╨╡╨╜╨╖╨╕╨╜  \n- **VIN**: LFV2***********7244  \n- **╨Ф╨░╤В╨░ ╨╖╨░╨┐╤А╨╛╤Б╨░ ╨╛╤В╤З╤С╤В╨░**: 20 ╤П╨╜╨▓╨░╤А╤П 2026 ╨│.  \n- **╨Я╨╛╤Б╨╗╨╡╨┤╨╜╨╕╨╣ ╨╖╨░╤Д╨╕╨║╤Б╨╕╤А╨╛╨▓╨░╨╜╨╜╤Л╨╣ ╨┐╤А╨╛╨▒╨╡╨│**: 4301 ╨║╨╝ (╨╜╨╛╤П╨▒╤А╤М 2023 ╨│.)  \n- **╨Р╨╜╨╛╨╝╨░╨╗╨╕╨╣ ╨┐╤А╨╛╨▒╨╡╨│╨░**: ╨╜╨╡ ╨╛╨▒╨╜╨░╤А╤Г╨╢╨╡╨╜╨╛  \n\n---\n\n### **╨Ю╤Ж╨╡╨╜╨║╨░ ╤Б╨╛╤Б╤В╨╛╤П╨╜╨╕╤П**  \n- **╨Ю╨▒╤Й╨░╤П ╨╛╤Ж╨╡╨╜╨║╨░**: ╨║╨╗╨░╤Б╤Б **A** (4.9 ╨╕╨╖ 5)  \n- **╨Я╤А╨╕╨▓╤Л╤З╨║╨╕ ╨╛╨▒╤Б╨╗╤Г╨╢╨╕╨▓╨░╨╜╨╕╤П**: ╤Г╨┤╨╛╨▓╨╗╨╡╤В╨▓╨╛╤А╨╕╤В╨╡╨╗╤М╨╜╤Л╨╡  \n- **╨Я╨╛╤Б╨╗╨╡╨┤	1943	1077	0.012502	qwen3-max-2026-01-23	SUCCESS	\N	30638	2026-02-05 05:30:53.085021+00
51	1	VIDEO	╨║╨╛╤В ╨╕╨│╤А╨░╨╡╤В ╨╜╨░ ╨┐╨╕╨░╨╜╨╕╨╜╨╛	\N	\N	\N	\N	sora-2-all	FAILED	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 2026020513313084131287jXTpB855)","type":"comet_api_error"}}	\N	2026-02-05 05:31:32.292396+00
52	1	VIDEO	╨║╨╛╤В ╨╕╨│╤А╨░╨╡╤В ╨╜╨░ ╨┐╨╕╨░╨╜╨╕╨╜╨╛ ╨▓ ╨┤╨╢╨░╨╖╨╛╨▓╨╛╨╝ ╨║╨╗╤Г╨▒╨╡, ╨╜╤Г╨░╤А ╤Б╤В╨╕╨╗╤М	\N	\N	\N	\N	sora-2-all	FAILED	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 20260205133303693880863lP5cJdSq)","type":"comet_api_error"}}	\N	2026-02-05 05:33:05.918632+00
53	1	VIDEO	╨║╨╛╤В ╨▒╨╡╨│╨░╨╡╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	\N	\N	\N	\N	sora-2	FAILED	Telegram server says - Bad Request: BUTTON_DATA_INVALID	\N	2026-02-05 06:15:11.325826+00
112	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╨┐╤А╨╕╨▓╨╡╤В	╨Я╤А╨╕╨▓╨╡╤В! ╨з╨╡╨╝ ╨╝╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М?	\N	\N	0.000190	qwen3-max-2026-01-23	SUCCESS	\N	\N	2026-02-09 14:03:03.6942+00
54	1	TEXT	╨║╤А╤Г╤В╨╛╨╡ ╤В╨│ ╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╨╡ ╤Б ╤Д╨╛╤А╨╝╨░╤В╨╕╤А╨╛╨▓╨░╨╜╨╕╨╡╨╝	╨Т╨╛╤В ╨┐╤А╨╕╨╝╨╡╤А ╨║╤А╤Г╤В╨╛╨│╨╛ Telegram-╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╤П ╤Б ╤Д╨╛╤А╨╝╨░╤В╨╕╤А╨╛╨▓╨░╨╜╨╕╨╡╨╝:\n\n---\n\nЁЯФе **╨Т╨Э╨Ш╨Ь╨Р╨Э╨Ш╨Х, ╨Ъ╨Ю╨Ь╨Р╨Э╨Ф╨Р!** ЁЯФе\n\n╨б╨╡╨│╨╛╨┤╨╜╤П ╤Г ╨╜╨░╤Б **╨▓╨░╨╢╨╜╨╛╨╡ ╨╛╨▒╨╜╨╛╨▓╨╗╨╡╨╜╨╕╨╡**! ЁЯЪА\n\nЁЯУМ **╨з╤В╨╛ ╨╜╨╛╨▓╨╛╨│╨╛:**\n- тЬЕ ╨Ч╨░╨┐╤Г╤Й╨╡╨╜ ╨╜╨╛╨▓╤Л╨╣ ╤Д╤Г╨╜╨║╤Ж╨╕╨╛╨╜╨░╨╗  \n- ЁЯОп ╨г╨╗╤Г╤З╤И╨╡╨╜╨░ ╨┐╤А╨╛╨╕╨╖╨▓╨╛╨┤╨╕╤В╨╡╨╗╤М╨╜╨╛╤Б╤В╤М  \n- ЁЯЫбя╕П ╨Ш╤Б╨┐╤А╨░╨▓╨╗╨╡╨╜╤Л ╨║╤А╨╕╤В╨╕╤З╨╡╤Б╨║╨╕╨╡ ╨▒╨░╨│╨╕  \n\nЁЯУЕ **╨Ф╨╡╨┤╨╗╨░╨╣╨╜:** *╨┐╤П╤В╨╜╨╕╤Ж╨░, 18:00*  \nЁЯУН **╨Ь╨╡╤Б╤В╨╛:** `#dev-team` ╨▓ Slack\n\nЁЯТм *╨Э╨╡ ╨╖╨░╨▒╤Г╨┤╤М╤В╨╡ ╨╛╨▒╨╜╨╛╨▓╨╕╤В╤М ╨┐╤А╨╕╨╗╨╛╨╢╨╡╨╜╨╕╨╡ ╨╕ ╨┐╤А╨╛╤В╨╡╤Б╤В╨╕╤А╨╛╨▓╨░╤В╤М ╤Б╨▓╨╛╨╕ ╨╝╨╛╨┤╤Г╨╗╨╕!*\n\nЁЯСЙ [╨б╤Б╤Л╨╗╨║╨░ ╨╜╨░ ╤А╨╡╨╗╨╕╨╖](https://example.com)  \nЁЯУО ╨Я╤А╨╕╨║╤А╨╡╨┐╨╗╤С╨╜╨╜╤Л╨╣ ╤Д╨░╨╣╨╗: `changelog_v2.1.txt`\n\n---\n\n╨Т Telegram ╨┐╨╛╨┤╨┤╨╡╤А╨╢╨╕╨▓╨░╤О╤В	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	11031	2026-02-05 06:16:36.905103+00
55	1	TEXT	╨╡╤Й╨╡ ╤А╨░╨╖╨╛╨║ ╤В╨╛╨╢╨╡ ╤Б╨░╨╝╨╛╨╡	╨Ъ╨╛╨╜╨╡╤З╨╜╨╛! ╨Т╨╛╤В ╨╡╤Й╤С ╨╛╨┤╨╕╨╜ ╨▓╨░╤А╨╕╨░╨╜╤В ╨║╤А╤Г╤В╨╛╨│╨╛ Telegram-╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╤П ╤Б ╤Д╨╛╤А╨╝╨░╤В╨╕╤А╨╛╨▓╨░╨╜╨╕╨╡╨╝ тАФ ╨▓ ╨┐╨╛╤Е╨╛╨╢╨╡╨╝ ╤Б╤В╨╕╨╗╨╡, ╨╜╨╛ ╤Б ╨╜╨╡╨╝╨╜╨╛╨│╨╛ ╨┤╤А╤Г╨│╨╕╨╝ ╨╛╤Д╨╛╤А╨╝╨╗╨╡╨╜╨╕╨╡╨╝:\n\n---\n\nЁЯОп **╨У╨Ю╨а╨п╨з╨Р╨п ╨Э╨Ю╨Т╨Ю╨б╨в╨м!** ЁЯОп\n\n╨Ф╤А╤Г╨╖╤М╤П, ╤Г ╨╜╨░╤Б **╨╝╨╡╨│╨░-╨░╨┐╨┤╨╡╨╣╤В**! ЁЯТе\n\nтЬи **╨з╤В╨╛ ╨╕╨╖╨╝╨╡╨╜╨╕╨╗╨╛╤Б╤М:**\n- ЁЯЪА ╨г╤Б╨║╨╛╤А╨╡╨╜╨░ ╨╖╨░╨│╤А╤Г╨╖╨║╨░ ╨╜╨░ **40%**  \n- ЁЯОи ╨Ю╨▒╨╜╨╛╨▓╨╗╤С╨╜ ╨╕╨╜╤В╨╡╤А╤Д╨╡╨╣╤Б тАФ ╤Б╤В╨░╨╗ ╨╡╤Й╤С ╤Г╨┤╨╛╨▒╨╜╨╡╨╡  \n- ЁЯФз ╨Я╨╛╤З╨╕╨╜╨╕╨╗╨╕ ╨╝╨╡╨╗╨║╨╕╨╡, ╨╜╨╛ ╨╜╨░╨┤╨╛╨╡╨┤╨╗╨╕╨▓╤Л╨╡ ╨▒╨░╨│╨╕  \n\nтП│ **╨б╤А╨╛╨║ ╤Б╨┤╨░╤З╨╕:** *╨╖╨░╨▓╤В╤А╨░ ╨┤╨╛ 15:00*  \nЁЯТм ╨Ю╨▒╤Б╤Г╨╢╨┤╨╡╨╜╨╕╨╡ тАФ ╨▓ ╨║╨░╨╜╨░╨╗╨╡ `#product-updates`\n\nЁЯУО ╨Э╨╡ ╨╖╨░╨▒╤Г╨┤╤М:  \nЁЯУД [╨Я╨╛╨╗╨╜╤Л╨╣ changelog](https://example.com/changelog)  \nЁЯУж ╨Т╨╡╤А╤Б╨╕╤П: `	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	11755	2026-02-05 06:17:05.440992+00
56	1	VIDEO	╨Ъ╨╛╤В ╨╕╨│╤А╨░╨╡╤В ╨╜╨░ ╨┐╨╕╨░╨╜╨╕╨╜╨╛ ╨▓ ╨┤╨╢╨░╨╖╨╛╨▓╨╛╨╝ ╨║╨╗╤Г╨▒╨╡, ╨╜╤Г╨░╤А ╤Б╤В╨╕╨╗╤М	\N	\N	\N	\N	sora-2	SUCCESS	\N	\N	2026-02-05 06:52:43.644656+00
57	1	TEXT	09:58	It seems like you've entered a time: **09:58**.  \n\nHow can I assist you with this? For example:  \n- Do you need help setting a reminder or alarm?  \n- Are you tracking time for a task?  \n- Is this related to scheduling or time zones?  \n\nLet me know! ЁЯШК	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	6502	2026-02-05 06:56:40.506419+00
58	1	VOICE	\N	╨н╤В╨╛ ╨▒╤Г╨┤╨╕╨╗╤М╨╜╨╕╨║.	\N	\N	0.000056	whisper-1	SUCCESS	\N	\N	2026-02-05 06:59:08.285156+00
59	1	DOCUMENT	╨Я╤А╨╛╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╤Г╨╣ ╤Н╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡. ╨Ю╨┐╨╕╤И╨╕ ╨╡╨│╨╛ ╤Б╨╛╨┤╨╡╤А╨╢╨╕╨╝╨╛╨╡ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛. ╨Х╤Б╨╗╨╕ ╤Н╤В╨╛ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В, ╨╕╨╖╨▓╨╗╨╡╨║╨╕ ╨╕ ╤Б╤В╤А╤Г╨║╤В╤Г╤А╨╕╤А╤Г╨╣ ╤В╨╡╨║╤Б╤В.	╨Ъ ╤Б╨╛╨╢╨░╨╗╨╡╨╜╨╕╤О, ╤П ╨╜╨╡ ╨▓╨╕╨╢╤Г ╨╜╨╕╨║╨░╨║╨╛╨│╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╤П. ╨Я╨╛╨╢╨░╨╗╤Г╨╣╤Б╤В╨░, ╨╖╨░╨│╤А╤Г╨╖╨╕╤В╨╡ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡, ╨║╨╛╤В╨╛╤А╨╛╨╡ ╨▓╤Л ╤Е╨╛╤В╨╕╤В╨╡, ╤З╤В╨╛╨▒╤Л ╤П ╨┐╤А╨╛╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╨╛╨▓╨░╨╗. ╨Я╨╛╤Б╨╗╨╡ ╤Н╤В╨╛╨│╨╛ ╤П ╤Б╨╝╨╛╨│╤Г:\n\n- ╨Я╨╛╨┤╤А╨╛╨▒╨╜╨╛ ╨╛╨┐╨╕╤Б╨░╤В╤М ╨╡╨│╨╛ ╤Б╨╛╨┤╨╡╤А╨╢╨╕╨╝╨╛╨╡ (╨╛╨▒╤К╨╡╨║╤В╤Л, ╨╗╤О╨┤╨╡╨╣, ╤Б╤Ж╨╡╨╜╤Л, ╤Ж╨▓╨╡╤В╨░, ╨║╨╛╨╝╨┐╨╛╨╖╨╕╤Ж╨╕╤О ╨╕ ╤В.╨┤.);\n- ╨Х╤Б╨╗╨╕ ╤Н╤В╨╛ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В тАФ ╤А╨░╤Б╨┐╨╛╨╖╨╜╨░╤В╤М ╤В╨╡╨║╤Б╤В ╤Б ╨┐╨╛╨╝╨╛╤Й╤М╤О OCR;\n- ╨б╤В╤А╤Г╨║╤В╤Г╤А╨╕╤А╨╛╨▓╨░╤В╤М ╨╕╨╖╨▓╨╗╨╡╤З╤С╨╜╨╜╤Л╨╣ ╤В╨╡╨║╤Б╤В (╨╜╨░╨┐╤А╨╕╨╝╨╡╤А, ╨▓╤Л╨┤╨╡╨╗╨╕╤В╤М ╨╖╨░╨│╨╛╨╗╨╛╨▓╨║╨╕, ╨░╨▒╨╖╨░╤Ж╤Л, ╤В╨░╨▒╨╗╨╕╤Ж╤Л, ╨┤╨░╤В╤Л, ╨╕╨╝╨╡╨╜╨░ ╨╕ ╨┤╤А╤Г╨│╨╕╨╡ ╨╖╨╜╨░╤З╨╕╨╝╤Л╨╡ ╤Н╨╗╨╡╨╝╨╡╨╜╤В╤Л).\n\n╨Я╨╛╨╢╨░╨╗╤Г╨╣╤Б╤В╨░, ╨┐╤А╨╕╨║╤А╨╡╨┐╨╕╤В╨╡ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡!	\N	\N	0.001320	qwen3-max-2026-01-23	SUCCESS	\N	11654	2026-02-05 07:24:01.428322+00
60	1	DOCUMENT	╨Я╤А╨╛╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╤Г╨╣ ╤Н╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡. ╨Ю╨┐╨╕╤И╨╕ ╨╡╨│╨╛ ╤Б╨╛╨┤╨╡╤А╨╢╨╕╨╝╨╛╨╡ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛. ╨Х╤Б╨╗╨╕ ╤Н╤В╨╛ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В, ╨╕╨╖╨▓╨╗╨╡╨║╨╕ ╨╕ ╤Б╤В╤А╤Г╨║╤В╤Г╤А╨╕╤А╤Г╨╣ ╤В╨╡╨║╤Б╤В.	╨Ъ ╤Б╨╛╨╢╨░╨╗╨╡╨╜╨╕╤О, ╤П ╨╜╨╡ ╨▓╨╕╨╢╤Г ╨╜╨╕╨║╨░╨║╨╛╨│╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╤П. ╨Я╨╛╨╢╨░╨╗╤Г╨╣╤Б╤В╨░, ╨╖╨░╨│╤А╤Г╨╖╨╕╤В╨╡ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡, ╨║╨╛╤В╨╛╤А╨╛╨╡ ╨▓╤Л ╤Е╨╛╤В╨╕╤В╨╡, ╤З╤В╨╛╨▒╤Л ╤П ╨┐╤А╨╛╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╨╛╨▓╨░╨╗. ╨Я╨╛╤Б╨╗╨╡ ╤Н╤В╨╛╨│╨╛ ╤П ╤Б╨╝╨╛╨│╤Г:\n\n- ╨Ю╨┐╨╕╤Б╨░╤В╤М ╨╡╨│╨╛ ╤Б╨╛╨┤╨╡╤А╨╢╨╕╨╝╨╛╨╡ (╨╛╨▒╤К╨╡╨║╤В╤Л, ╨╗╤О╨┤╨╡╨╣, ╤Б╤Ж╨╡╨╜╤Л, ╤Ж╨▓╨╡╤В╨░ ╨╕ ╤В.╨┤.);\n- ╨Х╤Б╨╗╨╕ ╤Н╤В╨╛ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В тАФ ╨╕╨╖╨▓╨╗╨╡╤З╤М ╨▓╨╡╤Б╤М ╤В╨╡╨║╤Б╤В;\n- ╨б╤В╤А╤Г╨║╤В╤Г╤А╨╕╤А╨╛╨▓╨░╤В╤М ╨╕╨╜╤Д╨╛╤А╨╝╨░╤Ж╨╕╤О (╨╜╨░╨┐╤А╨╕╨╝╨╡╤А, ╨▓╤Л╨┤╨╡╨╗╨╕╤В╤М ╨╖╨░╨│╨╛╨╗╨╛╨▓╨║╨╕, ╨┐╤Г╨╜╨║╤В╤Л, ╤В╨░╨▒╨╗╨╕╤Ж╤Л, ╨┤╨░╤В╤Л ╨╕ ╤В.╨┐.).\n\n╨Я╨╛╨╢╨░╨╗╤Г╨╣╤Б╤В╨░, ╨┐╤А╨╕╨║╤А╨╡╨┐╨╕╤В╨╡ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡!	\N	\N	0.001136	qwen3-max-2026-01-23	SUCCESS	\N	13165	2026-02-05 07:31:17.563148+00
61	1	DOCUMENT	╨Я╤А╨╛╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╤Г╨╣ ╤Н╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡. ╨Ю╨┐╨╕╤И╨╕ ╨╡╨│╨╛ ╤Б╨╛╨┤╨╡╤А╨╢╨╕╨╝╨╛╨╡ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛. ╨Х╤Б╨╗╨╕ ╤Н╤В╨╛ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В, ╨╕╨╖╨▓╨╗╨╡╨║╨╕ ╨╕ ╤Б╤В╤А╤Г╨║╤В╤Г╤А╨╕╤А╤Г╨╣ ╤В╨╡╨║╤Б╤В.	╨Ъ ╤Б╨╛╨╢╨░╨╗╨╡╨╜╨╕╤О, ╤П ╨╜╨╡ ╨╝╨╛╨│╤Г ╨┐╤А╨╛╤Б╨╝╨░╤В╤А╨╕╨▓╨░╤В╤М ╨╕╨╗╨╕ ╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╨╛╨▓╨░╤В╤М ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╤П ╨╜╨░╨┐╤А╤П╨╝╤Г╤О. ╨Ю╨┤╨╜╨░╨║╨╛ ╨▓╤Л ╨╝╨╛╨╢╨╡╤В╨╡:\n\n1. **╨Ю╨┐╨╕╤Б╨░╤В╤М ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡ ╤Б╨╗╨╛╨▓╨░╨╝╨╕** тАФ ╤А╨░╤Б╤Б╨║╨░╨╢╨╕╤В╨╡, ╤З╤В╨╛ ╨╜╨░ ╨╜╤С╨╝ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ (╨╜╨░╨┐╤А╨╕╨╝╨╡╤А, ╤В╨╕╨┐ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В╨░, ╤П╨╖╤Л╨║, ╨║╨╗╤О╤З╨╡╨▓╤Л╨╡ ╤Н╨╗╨╡╨╝╨╡╨╜╤В╤Л, ╨╗╨╛╨│╨╛╤В╨╕╨┐╤Л, ╤В╨░╨▒╨╗╨╕╤Ж╤Л ╨╕ ╤В.╨┤.), ╨╕ ╤П ╨┐╨╛╨╝╨╛╨│╤Г ╨▓╨░╨╝ ╨╡╨│╨╛ ╨┐╤А╨╛╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╨╛╨▓╨░╤В╤М.\n2. **╨Ш╨╖╨▓╨╗╨╡╤З╤М ╤В╨╡╨║╤Б╤В ╤Б ╨┐╨╛╨╝╨╛╤Й╤М╤О OCR** тАФ ╨╡╤Б╨╗╨╕ ╤Г ╨▓╨░╤Б ╨╡╤Б╤В╤М ╨┤╨╛╤Б╤В╤Г╨┐ ╨║ ╨╕╨╜╤Б╤В╤А╤Г╨╝╨╡╨╜╤В╨░╨╝ ╤А╨░╤Б╨┐╨╛╨╖╨╜╨░╨▓╨░╨╜╨╕╤П ╤В╨╡╨║╤Б╤В╨░ (╨╜╨░╨┐╤А╨╕╨╝╨╡╤А, Google Lens, Adobe Scan, ╨╛╨╜╨╗╨░╨╣╨╜-OCR ╤Б╨╡╤А╨▓╨╕╤Б╤Л), ╨▓╤Л ╨╝╨╛╨╢╨╡╤В╨╡ ╤Б╨║╨╛╨┐╨╕╤А╨╛╨▓╨░╤В╤М ╤А╨░╤Б╨┐╨╛╨╖╨╜╨░╨╜╨╜╤Л╨╣ ╤В╨╡╨║╤Б╤В ╤Б╤О╨┤╨░, ╨╕ ╤П ╤Б╤В╤А╤Г╨║╤В╤Г╤А╨╕╤А╤Г╤О ╨╡	\N	\N	0.001992	qwen3-max-2026-01-23	SUCCESS	\N	14269	2026-02-05 07:51:25.531597+00
62	1	DOCUMENT	╨Я╨╡╤А╨╡╨▓╨╡╨┤╨╕ ╤Н╤В╨╛╤В ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В ╨╜╨░ ╤А╤Г╤Б╤Б╨║╨╕╨╣ ╤П╨╖╤Л╨║, ╤Б╨╛╤Е╤А╨░╨╜╤П╤П ╤Б╤В╤А╤Г╨║╤В╤Г╤А╤Г.	╨н╨║╤Б╨┐╨╡╤А╤В╨╜╤Л╨╣ ╨╛╤В╤З╤С╤В ╨╛╨▒ ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╨╡  \n╨Ю╤В╤З╤С╤В ╨╛ ╤Б╨╛╤Б╤В╨╛╤П╨╜╨╕╨╕ ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╤П  \n\n**╨Ю╨▒╤Й╨░╤П ╨╕╨╜╤Д╨╛╤А╨╝╨░╤Ж╨╕╤П**  \n╨Ъ╨╛╨╝╨┐╨╗╨╡╨║╤В╨░╤Ж╨╕╤П: Audi тАФ ╨╜╨╡╤В ╨╕╨╜╤Д╨╛╤А╨╝╨░╤Ж╨╕╨╕  \nVIN: LFV2***********8043  \n╨в╨╕╨┐ ╨в╨б: ╨Ы╨╡╨│╨║╨╛╨▓╨╛╨╣ ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╤М  \n╨Я╤А╨╛╨╕╤Б╤Е╨╛╨╢╨┤╨╡╨╜╨╕╨╡: ╨Ъ╨╕╤В╨░╨╣ (╨╗╨╛╨║╨░╨╗╤М╨╜╨╛╨╡ ╨┐╤А╨╛╨╕╨╖╨▓╨╛╨┤╤Б╤В╨▓╨╛)  \n╨в╨╕╨┐ ╨╕╤Б╨┐╨╛╨╗╤М╨╖╨╛╨▓╨░╨╜╨╕╤П: ╨Ы╨╕╤З╨╜╨╛╨╡ (╨╜╨╡ ╨║╨╛╨╝╨╝╨╡╤А╤З╨╡╤Б╨║╨╛╨╡ ╨╕╤Б╨┐╨╛╨╗╤М╨╖╨╛╨▓╨░╨╜╨╕╨╡)  \n╨Ъ╨╛╨╗╨╕╤З╨╡╤Б╤В╨▓╨╛ ╨▓╨╗╨░╨┤╨╡╨╗╤М╤Ж╨╡╨▓: 1  \n╨б╤А╨╛╨║ ╤Б ╨┐╨╡╤А╨▓╨╛╨╣ ╤А╨╡╨│╨╕╤Б╤В╤А╨░╤Ж╨╕╨╕: ╨╜╨╡╤В ╨╕╨╜╤Д╨╛╤А╨╝╨░╤Ж╨╕╨╕  \n╨Э╨╛╨▓╤Л╨╣ ╤Н╨╜╨╡╤А╨│╨╡╤В╨╕╤З╨╡╤Б╨║╨╕╨╣ ╤В╤А╨░╨╜╤Б╨┐╨╛╤А╤В: ╨Э╨╡╤В  \n\n**╨Я╤А╨╛╨▓╨╡╤А╨║╨░ ╨╜╨░ ╤Б╨╡╤А╤М╤С╨╖╨╜╤Л╨╡ ╤А╨╕╤Б╨║╨╕**  \n╨б╤В╤А╤Г╨║╤В╤Г╤А╨╜╤Л╨╡ ╨┐╨╛╨▓╤А╨╡╨╢╨┤╨╡╨╜╨╕╤П: ╨╜╨╡ ╨╛╨▒╨╜╨░╤А╤Г╨╢╨╡╨╜╨╛  \n╨б╤А╨░╨▒╨░╤В╤Л╨▓╨░╨╜╨╕╨╡ ╨┐╨╛╨┤╤Г╤И╨╡╨║ ╨▒╨╡╨╖	1498	1567	0.015532	qwen3-max-2026-01-23	SUCCESS	\N	42469	2026-02-05 07:54:24.78257+00
63	1	DOCUMENT	╨Я╤А╨╛╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╤Г╨╣ ╤Н╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡. ╨Ю╨┐╨╕╤И╨╕ ╨╡╨│╨╛ ╤Б╨╛╨┤╨╡╤А╨╢╨╕╨╝╨╛╨╡ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛. ╨Х╤Б╨╗╨╕ ╤Н╤В╨╛ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В, ╨╕╨╖╨▓╨╗╨╡╨║╨╕ ╨╕ ╤Б╤В╤А╤Г╨║╤В╤Г╤А╨╕╤А╤Г╨╣ ╤В╨╡╨║╤Б╤В.	╨Ъ ╤Б╨╛╨╢╨░╨╗╨╡╨╜╨╕╤О, ╤П ╨╜╨╡ ╨▓╨╕╨╢╤Г ╨╜╨╕╨║╨░╨║╨╛╨│╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╤П. ╨Я╨╛╨╢╨░╨╗╤Г╨╣╤Б╤В╨░, ╨╖╨░╨│╤А╤Г╨╖╨╕╤В╨╡ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡, ╨║╨╛╤В╨╛╤А╨╛╨╡ ╨▓╤Л ╤Е╨╛╤В╨╕╤В╨╡, ╤З╤В╨╛╨▒╤Л ╤П ╨┐╤А╨╛╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╨╛╨▓╨░╨╗. ╨Я╨╛╤Б╨╗╨╡ ╤Н╤В╨╛╨│╨╛ ╤П ╤Б╨╝╨╛╨│╤Г:\n\n- ╨Ю╨┐╨╕╤Б╨░╤В╤М ╨╡╨│╨╛ ╤Б╨╛╨┤╨╡╤А╨╢╨╕╨╝╨╛╨╡ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛;\n- ╨Х╤Б╨╗╨╕ ╤Н╤В╨╛ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В тАФ ╨╕╨╖╨▓╨╗╨╡╤З╤М ╨╕ ╤Б╤В╤А╤Г╨║╤В╤Г╤А╨╕╤А╨╛╨▓╨░╤В╤М ╤В╨╡╨║╤Б╤В (╨╜╨░╨┐╤А╨╕╨╝╨╡╤А, ╨▓╤Л╨┤╨╡╨╗╨╕╤В╤М ╨╖╨░╨│╨╛╨╗╨╛╨▓╨║╨╕, ╨░╨▒╨╖╨░╤Ж╤Л, ╤В╨░╨▒╨╗╨╕╤Ж╤Л, ╨┐╨╛╨┤╨┐╨╕╤Б╨╕ ╨╕ ╤В.╨┤.);\n- ╨г╨║╨░╨╖╨░╤В╤М ╤В╨╕╨┐ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В╨░ (╤Б╤З╤С╤В, ╨┐╨░╤Б╨┐╨╛╤А╤В, ╨┤╨╛╨│╨╛╨▓╨╛╤А, ╤Д╨╛╤В╨╛╨│╤А╨░╤Д╨╕╤П ╨╕ ╨┐╤А.);\n- ╨Я╤А╨╕ ╨╜╨╡╨╛╨▒╤Е╨╛╨┤╨╕╨╝╨╛╤Б╤В╨╕ тАФ ╨┐╨╡╤А╨╡╨▓╨╡╤Б╤В╨╕ ╨╕╨╗╨╕ ╨╕╨╜╤В╨╡╤А╨┐╤А╨╡╤В╨╕╤А╨╛╨▓╨░╤В╤М ╨╕╨╜╤Д╨╛╤А╨╝╨░╤Ж╨╕╤О.\n\n╨Я╨╛╨╢╨░╨╗╤Г╨╣╤Б╤В╨░, ╨┐╤А╨╕╨║╤А╨╡╨┐╨╕╤В╨╡ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡!	\N	\N	0.001248	qwen3-max-2026-01-23	SUCCESS	\N	12202	2026-02-05 07:56:16.151072+00
64	1	DOCUMENT	╨б╤Г╨╝╨╝╨░╤А╨╕╨╖╨╕╤А╤Г╨╣ ╤Н╤В╨╛╤В ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В. ╨Т╤Л╨┤╨╡╨╗╨╕ ╨║╨╗╤О╤З╨╡╨▓╤Л╨╡ ╨┐╤Г╨╜╨║╤В╤Л ╨╕ ╨│╨╗╨░╨▓╨╜╤Л╨╡ ╨▓╤Л╨▓╨╛╨┤╤Л.	╨Т╨╛╤В ╨║╤А╨░╤В╨║╨╛╨╡ ╤А╨╡╨╖╤О╨╝╨╡ ╨╕ ╨║╨╗╤О╤З╨╡╨▓╤Л╨╡ ╨▓╤Л╨▓╨╛╨┤╤Л ╨╕╨╖ ╤Н╨║╤Б╨┐╨╡╤А╤В╨╜╨╛╨│╨╛ ╨╛╤В╤З╤С╤В╨░ ╨╛╨▒ ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╨╡:\n\n---\n\n### **╨Ю╨▒╤Й╨░╤П ╨╕╨╜╤Д╨╛╤А╨╝╨░╤Ж╨╕╤П**\n- **╨Ь╨░╤А╨║╨░:** Audi (╨╕╨╜╤Д╨╛╤А╨╝╨░╤Ж╨╕╤П ╨╛ ╨╝╨╛╨┤╨╡╨╗╨╕ ╨╛╤В╤Б╤Г╤В╤Б╤В╨▓╤Г╨╡╤В)  \n- **VIN:** LFV2***********8043  \n- **╨Я╤А╨╛╨╕╤Б╤Е╨╛╨╢╨┤╨╡╨╜╨╕╨╡:** ╨Ъ╨╕╤В╨░╨╣ (╨╗╨╛╨║╨░╨╗╤М╨╜╨╛╨╡ ╨┐╤А╨╛╨╕╨╖╨▓╨╛╨┤╤Б╤В╨▓╨╛)  \n- **╨в╨╕╨┐ ╨╕╤Б╨┐╨╛╨╗╤М╨╖╨╛╨▓╨░╨╜╨╕╤П:** ╨Ы╨╕╤З╨╜╤Л╨╣ (╨╜╨╡ ╨║╨╛╨╝╨╝╨╡╤А╤З╨╡╤Б╨║╨╕╨╣)  \n- **╨Ъ╨╛╨╗╨╕╤З╨╡╤Б╤В╨▓╨╛ ╨▓╨╗╨░╨┤╨╡╨╗╤М╤Ж╨╡╨▓:** 1  \n- **╨Я╤А╨╛╨▒╨╡╨│:**  \n  - ╨Я╨╛╤Б╨╗╨╡╨┤╨╜╨╕╨╣ ╨╖╨░╤Д╨╕╨║╤Б╨╕╤А╨╛╨▓╨░╨╜╨╜╤Л╨╣: **7573 ╨║╨╝** (╨┐╨╛ ╤Б╨╛╤Б╤В╨╛╤П╨╜╨╕╤О ╨╜╨░ ╨┤╨╡╨║╨░╨▒╤А╤М 2024 ╨│.)  \n  - ╨Я╤А╨╛╨│╨╜╨╛╨╖╨╕╤А╤Г╨╡╨╝╤Л╨╣ ╤В╨╡╨║╤Г╤Й╨╕╨╣: **9503 ╨║╨╝**  \n  - ╨б╤А╨╡╨┤╨╜╨╡╨│╨╛╨┤╨╛╨▓╨╛╨╣ ╨┐╤А╨╛╨▒╨╡╨│: **2059	1500	1118	0.011944	qwen3-max-2026-01-23	SUCCESS	\N	33770	2026-02-05 08:08:24.297658+00
65	1	DOCUMENT	╨Я╤А╨╛╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╤Г╨╣ ╤Н╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡. ╨Ю╨┐╨╕╤И╨╕ ╨╡╨│╨╛ ╤Б╨╛╨┤╨╡╤А╨╢╨╕╨╝╨╛╨╡ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛. ╨Х╤Б╨╗╨╕ ╤Н╤В╨╛ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В, ╨╕╨╖╨▓╨╗╨╡╨║╨╕ ╨╕ ╤Б╤В╤А╤Г╨║╤В╤Г╤А╨╕╤А╤Г╨╣ ╤В╨╡╨║╤Б╤В.	╨Ъ ╤Б╨╛╨╢╨░╨╗╨╡╨╜╨╕╤О, ╤П ╨╜╨╡ ╨▓╨╕╨╢╤Г ╨╜╨╕╨║╨░╨║╨╛╨│╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╤П. ╨Я╨╛╨╢╨░╨╗╤Г╨╣╤Б╤В╨░, ╨╖╨░╨│╤А╤Г╨╖╨╕╤В╨╡ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡, ╨║╨╛╤В╨╛╤А╨╛╨╡ ╨▓╤Л ╤Е╨╛╤В╨╕╤В╨╡, ╤З╤В╨╛╨▒╤Л ╤П ╨┐╤А╨╛╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╨╛╨▓╨░╨╗. ╨Я╨╛╤Б╨╗╨╡ ╤Н╤В╨╛╨│╨╛ ╤П ╤Б╨╝╨╛╨│╤Г:\n\n- ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛ ╨╛╨┐╨╕╤Б╨░╤В╤М ╨╡╨│╨╛ ╤Б╨╛╨┤╨╡╤А╨╢╨╕╨╝╨╛╨╡;\n- ╨╛╨┐╤А╨╡╨┤╨╡╨╗╨╕╤В╤М, ╤П╨▓╨╗╤П╨╡╤В╤Б╤П ╨╗╨╕ ╨╛╨╜╨╛ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В╨╛╨╝;\n- ╨┐╤А╨╕ ╨╜╨╡╨╛╨▒╤Е╨╛╨┤╨╕╨╝╨╛╤Б╤В╨╕ ╨╕╨╖╨▓╨╗╨╡╤З╤М ╨╕ ╤Б╤В╤А╤Г╨║╤В╤Г╤А╨╕╤А╨╛╨▓╨░╤В╤М ╤В╨╡╨║╤Б╤В.\n\n╨Ч╨░╨│╤А╤Г╨╖╨╕╤В╨╡ ╤Д╨░╨╣╨╗, ╨╕ ╤П ╨┐╨╛╨╝╨╛╨│╤Г!	\N	\N	0.000856	qwen3-max-2026-01-23	SUCCESS	\N	63535	2026-02-05 08:10:50.822384+00
66	1	VIDEO	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	\N	\N	\N	\N	sora-2	SUCCESS	\N	\N	2026-02-06 14:55:15.36446+00
67	1	VIDEO	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	\N	\N	\N	\N	sora-2	SUCCESS	\N	\N	2026-02-06 15:17:16.599256+00
68	1	TEXT	╨╣	╨Я╤А╨╕╨▓╨╡╤В! ╨Я╨╛╤Е╨╛╨╢╨╡, ╨▓╤Л ╨╛╤В╨┐╤А╨░╨▓╨╕╨╗╨╕ ╤В╨╛╨╗╤М╨║╨╛ ╨▒╤Г╨║╨▓╤Г ┬л╨╣┬╗. ╨Ь╨╛╨│╤Г ╨╗╨╕ ╤П ╤З╨╡╨╝-╤В╨╛ ╨┐╨╛╨╝╨╛╤З╤М? ╨Ч╨░╨┤╨░╨╣╤В╨╡ ╨▓╨╛╨┐╤А╨╛╤Б ╨╕╨╗╨╕ ╤Г╤В╨╛╤З╨╜╨╕╤В╨╡, ╨╛ ╤З╤С╨╝ ╨▓╤Л ╤Е╨╛╤В╨╡╨╗╨╕ ╨▒╤Л ╨┐╨╛╨│╨╛╨▓╨╛╤А╨╕╤В╤М.	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	4973	2026-02-07 02:12:02.938793+00
69	1	VOICE	\N	\N	\N	\N	\N	unknown	FAILED	Connection error.	\N	2026-02-07 17:39:01.753458+00
70	1	IMAGE	╨Ъ╨╛╤В-╨║╨╛╤Б╨╝╨╛╨╜╨░╨▓╤В ╨╜╨░ ╨Ы╤Г╨╜╨╡, ╤Ж╨╕╤Д╤А╨╛╨▓╨╛╨╡ ╨╕╤Б╨║╤Г╤Б╤Б╤В╨▓╨╛	\N	\N	\N	\N	unknown	FAILED	Request timed out.	\N	2026-02-07 18:07:35.519574+00
71	1	IMAGE	╨Ъ╨╛╤В-╨║╨╛╤Б╨╝╨╛╨╜╨░╨▓╤В ╨╜╨░ ╨Ы╤Г╨╜╨╡, ╤Ж╨╕╤Д╤А╨╛╨▓╨╛╨╡ ╨╕╤Б╨║╤Г╤Б╤Б╤В╨▓╨╛	\N	\N	\N	0.040000	qwen-image	SUCCESS	\N	\N	2026-02-07 18:24:13.985833+00
72	1	VIDEO	╨Ъ╨╛╤В ╨╜╨░╤З╨╕╨╜╨░╨╡╤В ╤Е╨╛╨┤╨╕╤В╤М ╨┐╨╛ ╨╗╤Г╨╜╨╡	\N	\N	\N	\N	sora-2	SUCCESS	\N	\N	2026-02-07 18:28:46.893955+00
73	1	LONG_VIDEO	Test space video	\N	\N	\N	\N	sora-2	SUCCESS	\N	\N	2026-02-07 21:28:45.508331+00
74	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	\N	\N	\N	\N	gpt-4o-vision	FAILED	Telegram server says - Bad Request: BUTTON_DATA_INVALID	9580	2026-02-07 22:30:16.251221+00
75	1	IMAGE	╨┐╨╛╨┤╨╗╨╛╨┤╨║╨░ ╨╜╨░╤З╨╕╨╜╨░╨╡╤В ╨┐╨╗╤Л╤В╤М	\N	\N	\N	\N	gpt-4o-vision	FAILED	Telegram server says - Bad Request: BUTTON_DATA_INVALID	60262	2026-02-07 22:30:24.089322+00
76	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	\N	\N	\N	\N	gpt-4o-vision	FAILED	Telegram server says - Bad Request: BUTTON_DATA_INVALID	10538	2026-02-07 22:30:41.988628+00
77	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	\N	\N	\N	\N	gpt-4o-vision	FAILED	Telegram server says - Bad Request: BUTTON_DATA_INVALID	12666	2026-02-07 22:31:07.678604+00
78	1	LONG_VIDEO	Test space video	\N	\N	\N	\N	sora-2	SUCCESS	\N	\N	2026-02-07 22:33:45.018351+00
79	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	╨Ъ ╤Б╨╛╨╢╨░╨╗╨╡╨╜╨╕╤О, ╤П ╨╜╨╡ ╨╝╨╛╨│╤Г ╨▓╨╕╨┤╨╡╤В╤М ╨╕╨╗╨╕ ╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╨╛╨▓╨░╤В╤М ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╤П. ╨Х╤Б╨╗╨╕ ╨▓╤Л ╨╖╨░╨│╤А╤Г╨╖╨╕╤В╨╡ ╤Д╨╛╤В╨╛, ╤П ╨╜╨╡ ╨┐╨╛╨╗╤Г╤З╤Г ╨║ ╨╜╨╡╨╝╤Г ╨┤╨╛╤Б╤В╤Г╨┐ тАФ ╤Г ╨╝╨╡╨╜╤П ╨╜╨╡╤В ╨▓╨╛╨╖╨╝╨╛╨╢╨╜╨╛╤Б╤В╨╕ ╨┐╤А╨╛╤Б╨╝╨░╤В╤А╨╕╨▓╨░╤В╤М ╨▓╨╗╨╛╨╢╨╡╨╜╨╕╤П ╨╕╨╗╨╕ ╨▓╨╜╨╡╤И╨╜╨╕╨╡ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╤П.\n\n╨Ю╨┤╨╜╨░╨║╨╛ ╨▓╤Л ╨╝╨╛╨╢╨╡╤В╨╡ ╨╛╨┐╨╕╤Б╨░╤В╤М ╨╝╨╜╨╡, ╤З╤В╨╛ ╨╜╨░╤Е╨╛╨┤╨╕╤В╤Б╤П ╨╜╨░ ╤Д╨╛╤В╨╛ (╨╜╨░╨┐╤А╨╕╨╝╨╡╤А: ┬л╨╜╨░ ╤Д╨╛╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╤С╨╜ ╨╖╨░╨║╨░╤В ╨╜╨░╨┤ ╨╝╨╛╤А╨╡╨╝, ╨╜╨░ ╨▒╨╡╤А╨╡╨│╤Г ╤Б╤В╨╛╨╕╤В ╤З╨╡╨╗╨╛╨▓╨╡╨║ ╨▓ ╨║╤А╨░╤Б╨╜╨╛╨╣ ╨║╤Г╤А╤В╨║╨╡┬╗), ╨╕ ╤П ╨┐╨╛╨╝╨╛╨│╤Г ╨▓╨░╨╝ ╤Б╨╛╤Б╤В╨░╨▓╨╕╤В╤М ╨▒╨╛╨╗╨╡╨╡ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛╨╡ ╨╛╨┐╨╕╤Б╨░╨╜╨╕╨╡, ╨┐╤А╨╛╨░╨╜╨░╨╗╨╕╨╖╨╕╤А╨╛╨▓╨░╤В╤М ╤Б╤Ж╨╡╨╜╤Г ╨╕╨╗╨╕ ╨┐╨╛╨╝╨╛╤З╤М ╤Б ╤З╨╡╨╝-╤В╨╛ ╨┤╤А╤Г╨│╨╕╨╝ тАФ ╨╜╨░╨┐╤А╨╕╨╝╨╡╤А, ╤Б ╤Е╤Г╨┤╨╛╨╢╨╡╤Б╤В╨▓╨╡╨╜╨╜╤Л╨╝ ╨╛╨┐╨╕╤Б╨░╨╜╨╕╨╡╨╝, ╨╛╨┐╤А╨╡╨┤╨╡╨╗╨╡╨╜╨╕╨╡╨╝ ╤Б╤В╨╕╨╗╤П, ╨╕╤Б╤В╨╛╤А╨╕╤З╨╡╤Б╨║╨╕	\N	\N	\N	gpt-4o-vision	SUCCESS	\N	11345	2026-02-07 22:34:13.181993+00
80	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	╨Э╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╕ тАФ ╨┐╤А╨░╨╖╨┤╨╜╨╕╤З╨╜╤Л╨╣ ╨┐╨╗╨░╨║╨░╤В, ╨┐╨╛╤Б╨▓╤П╤Й╤С╨╜╨╜╤Л╨╣ 35-╨╗╨╡╤В╨╕╤О ╨┐╨╛╨┤╨▓╨╛╨┤╨╜╨╛╨╣ ╨╗╨╛╨┤╨║╨╕ ┬л322 ╨н╨║╨╕╨┐╨░╨╢┬╗ ╨╕ ╨Ъ╤А╨░╤Б╨╜╨╛╨╖╨╜╨░╨╝╤С╨╜╨╜╨╛╨╝╤Г ╨б╨╡╨▓╨╡╤А╨╜╨╛╨╝╤Г ╤Д╨╗╨╛╤В╤Г. ╨н╤В╨╛ ╨╕╨╗╨╗╤О╤Б╤В╤А╨░╤Ж╨╕╤П ╨▓ ╤Б╤В╨╕╨╗╨╡ ╨║╨╛╨╝╨╕╨║╤Б╨░, ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜╨╜╨░╤П ╨▓ ╤П╤А╨║╨╕╤Е ╤Ж╨▓╨╡╤В╨░╤Е.\n\n╨Т ╤Ж╨╡╨╜╤В╤А╨╡ ╨║╨╛╨╝╨┐╨╛╨╖╨╕╤Ж╨╕╨╕ ╨╜╨░╤Е╨╛╨┤╨╕╤В╤Б╤П ╤З╤С╤А╨╜╨░╤П ╨┐╨╛╨┤╨▓╨╛╨┤╨╜╨░╤П ╨╗╨╛╨┤╨║╨░, ╤З╨░╤Б╤В╨╕╤З╨╜╨╛ ╨▓╤Л╨╜╤Л╤А╨╜╤Г╨▓╤И╨░╤П ╨╕╨╖ ╤Б╨╕╨╜╨╡╨│╨╛ ╨╝╨╛╤А╤П. ╨Э╨░ ╨▒╨╛╤А╤В╤Г ╨╗╨╛╨┤╨║╨╕ ╨▓╨╕╨┤╨╜╤Л ╤Ж╨╕╤Д╤А╤Л ┬л322┬╗ ╨╕ ┬л22┬╗. ╨Э╨░╨┤ ╨╗╨╛╨┤╨║╨╛╨╣, ╨╜╨░ ╤Д╨╛╨╜╨╡ ╨╜╨╡╨▒╨░ ╤Б ╨╖╨╡╨╗╤С╨╜╤Л╨╝╨╕ ╨╕ ╤Д╨╕╨╛╨╗╨╡╤В╨╛╨▓╤Л╨╝╨╕ ╨╛╤В╤В╨╡╨╜╨║╨░╨╝╨╕, ╨┐╨╛╤Е╨╛╨╢╨╕╨╝╨╕ ╨╜╨░ ╤Б╨╡╨▓╨╡╤А╨╜╨╛╨╡ ╤Б╨╕╤П╨╜╨╕╨╡, ╨╜╨░ ╨║╤А╨╡╤Б╤В╨╛╨╛╨▒╤А╨░╨╖╨╜╨╛ ╨┐╨╡╤А╨╡╤Б╨╡╤З╤С╨╜╨╜╤Л╤Е ╨┤╤А╨╡╨▓╨║╨░╤Е ╤А╨░╨╖╨▓╨╡╨▓╨░╤О╤В╤Б╤П ╨┤╨▓╨░ ╤Д╨╗╨░╨│╨░: ╤Б╨╗╨╡╨▓╨░ тАФ ╤Д╨╗╨░╨│ ╨а╨╛╤Б╤Б╨╕╨╣╤Б╨║╨╛╨╣ ╨д╨╡╨┤╨╡╤А╨░╤Ж╨╕	\N	\N	\N	qwen3-vl-30b-a3b	SUCCESS	\N	9449	2026-02-07 22:40:03.162955+00
81	1	VIDEO_ANIMATE	╨┐╨╛╨┤╨╗╨╛╨┤╨║╨░ ╤Г╨┐╨╗╤Л╨▓╨░╨╡╤В ╨▓╨┤╨░╨╗╤М	\N	\N	\N	\N	sora-2	SUCCESS	\N	\N	2026-02-07 22:45:36.950827+00
82	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	╨Э╨░ ╤Д╨╛╤В╨╛╨│╤А╨░╤Д╨╕╨╕ ╨╕╨╖╨╛╨▒╤А╨░╨╢╤С╨╜ ╨┐╨╛╤А╤В╤А╨╡╤В ╨Ъ╤А╨╕╤И╤В╨╕╨░╨╜╤Г ╨а╨╛╨╜╨░╨╗╨┤╤Г, ╤Б╨┤╨╡╨╗╨░╨╜╨╜╤Л╨╣ ╨▓ ╤Б╤В╤Г╨┤╨╕╨╣╨╜╤Л╤Е ╤Г╤Б╨╗╨╛╨▓╨╕╤П╤Е. ╨Ю╨╜ ╤Б╨╝╨╛╤В╤А╨╕╤В ╨┐╤А╤П╨╝╨╛ ╨▓ ╨║╨░╨╝╨╡╤А╤Г ╤Б ╤Б╨╡╤А╤М╤С╨╖╨╜╤Л╨╝ ╨╕ ╤Г╨▓╨╡╤А╨╡╨╜╨╜╤Л╨╝ ╨▓╤Л╤А╨░╨╢╨╡╨╜╨╕╨╡╨╝ ╨╗╨╕╤Ж╨░.\n\n**╨Ю╨┤╨╡╨╢╨┤╨░ ╨╕ ╨▓╨╜╨╡╤И╨╜╨╕╨╣ ╨▓╨╕╨┤:**\n- **╨Ъ╨╛╤Б╤В╤О╨╝:** ╨а╨╛╨╜╨░╨╗╨┤╤Г ╨╛╨┤╨╡╤В ╨▓ ╤З╤С╤А╨╜╤Л╨╣ ╨┐╨╕╨┤╨╢╨░╨║ ╤Б ╤В╨╛╨╜╨║╨╕╨╝╨╕ ╨▓╨╡╤А╤В╨╕╨║╨░╨╗╤М╨╜╤Л╨╝╨╕ ╨┐╨╛╨╗╨╛╤Б╨║╨░╨╝╨╕ (╨┐╨╕╨┤╨╢╨░╨║ ╨▓ ╨┐╨╛╨╗╨╛╤Б╨║╤Г).\n- **╨а╤Г╨▒╨░╤И╨║╨░:** ╨Я╨╛╨┤ ╨┐╨╕╨┤╨╢╨░╨║╨╛╨╝ ╨▓╨╕╨┤╨╜╨░ ╨▒╨╡╨╗╨░╤П ╨╕╨╗╨╕ ╤Б╨▓╨╡╤В╨╗╨╛-╨║╤А╨╡╨╝╨╛╨▓╨░╤П ╤А╤Г╨▒╨░╤И╨║╨░ ╤Б ╨╛╤В╨╗╨╛╨╢╨╜╤Л╨╝ ╨▓╨╛╤А╨╛╤В╨╜╨╕╨║╨╛╨╝.\n- **╨У╨░╨╗╤Б╤В╤Г╨║:** ╨Э╨░ ╨╜╤С╨╝ ╨│╨░╨╗╤Б╤В╤Г╨║ ╤Б ╨┐╨╛╨▓╤В╨╛╤А╤П╤О╤Й╨╕╨╝╤Б╤П ╤Г╨╖╨╛╤А╨╛╨╝, ╨╜╨░╨┐╨╛╨╝╨╕╨╜╨░╤О╤Й╨╕╨╝ ╨╗╨╛╨│╨╛╤В╨╕╨┐ ╨▒╤А╨╡╨╜╨┤╨░ Gucci (╨║╨▓╨░╨┤╤А╨░╤В╨╜╤Л╨╡ ╤Н╨╗╨╡╨╝╨╡╨╜╤В╤Л). ╨ж╨▓╨╡╤В ╨│╨░╨╗╤Б╤В╤Г╨║╨░ тАФ ╤В╤С╨╝╨╜╤Л╨╣, 	\N	\N	\N	qwen3-vl-30b-a3b	SUCCESS	\N	9263	2026-02-07 22:49:49.083802+00
83	1	VIDEO_ANIMATE	╨╝╤Г╨╢╤З╨╕╨╜╨░ ╨╜╨░ ╤Д╨╛╤В╨╛ ╤А╨░╨╖╨▓╨╛╤А╨░╤З╨╕╨▓╨░╨╡╤В╤Б╤П ╨╕ ╤Г╤Е╨╛╨┤╨╕╤В	\N	\N	\N	\N	sora-2	FAILED	Video generation failed: Your request was blocked by our moderation system.	\N	2026-02-07 22:50:38.123522+00
85	1	VIDEO_ANIMATE	╨╜╨░ ╨╖╨░╨┤╨╜╨╡╨╝ ╨┐╨╗╨░╨╜╨╡ ╨▒╨░╨╖╤Л ╨▓╤Б╤В╨░╨╡╤В ╤Б╨╛╨╗╨╜╤Ж╨╡	\N	\N	\N	\N	sora-2	SUCCESS	\N	\N	2026-02-07 23:01:44.942142+00
113	3	IMAGE	╨║╨╛╤В ╨▓ ╨║╨╛╤Б╨╝╨╛╤Б╨╡	\N	\N	\N	0.040000	dall-e-3	SUCCESS	\N	\N	2026-02-09 14:13:11.656171+00
115	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╨┐╤А╨╕╨▓╨╡╤В	╨Я╤А╨╕╨▓╨╡╤В! ╨з╨╡╨╝ ╨╝╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М?	\N	\N	0.000190	qwen3-max-2026-01-23	SUCCESS	\N	\N	2026-02-09 14:14:34.309839+00
84	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	╨Э╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╕ ╨┐╤А╨╡╨┤╤Б╤В╨░╨▓╨╗╨╡╨╜ ╤Д╨░╨╜╤В╨░╤Б╤В╨╕╤З╨╡╤Б╨║╨╕╨╣ ╨┐╨╡╨╣╨╖╨░╨╢, ╨▓╨╡╤А╨╛╤П╤В╨╜╨╛, ╨╜╨░ ╨┐╨╛╨▓╨╡╤А╤Е╨╜╨╛╤Б╤В╨╕ ╨Ь╨░╤А╤Б╨░ ╨╕╨╗╨╕ ╨┤╤А╤Г╨│╨╛╨╣ ╨┐╨╗╨░╨╜╨╡╤В╤Л. ╨Т ╤Ж╨╡╨╜╤В╤А╨╡ ╨║╨╛╨╝╨┐╨╛╨╖╨╕╤Ж╨╕╨╕ ╨╜╨░╤Е╨╛╨┤╨╕╤В╤Б╤П ╤Б╨╛╨▓╤А╨╡╨╝╨╡╨╜╨╜╤Л╨╣, ╤Д╤Г╤В╤Г╤А╨╕╤Б╤В╨╕╤З╨╡╤Б╨║╨╕╨╣ ╨╢╨╕╨╗╨╛╨╣ ╨╝╨╛╨┤╤Г╨╗╤М ╤Б ╨┐╨╗╨░╨▓╨╜╤Л╨╝╨╕, ╨╕╨╖╨╛╨│╨╜╤Г╤В╤Л╨╝╨╕ ╤Д╨╛╤А╨╝╨░╨╝╨╕. ╨Ч╨┤╨░╨╜╨╕╨╡ ╨╕╨╝╨╡╨╡╤В ╨░╤А╨╛╤З╨╜╤Г╤О ╨║╨╛╨╜╤Б╤В╤А╤Г╨║╤Ж╨╕╤О, ╨╜╨░╨┐╨╛╨╝╨╕╨╜╨░╤О╤Й╤Г╤О ╨║╨░╨┐╤Б╤Г╨╗╤Г ╨╕╨╗╨╕ ╨▒╨╕╨╛╨╜╨╕╤З╨╡╤Б╨║╤Г╤О ╨╛╨▒╨╛╨╗╨╛╤З╨║╤Г, ╨╕ ╤Г╤Б╤В╨░╨╜╨╛╨▓╨╗╨╡╨╜╨╛ ╨╜╨░ ╨║╤А╨░╤Б╨╜╨╛╨▓╨░╤В╨╛-╨╛╤А╨░╨╜╨╢╨╡╨▓╨╛╨╝ ╨┐╨╡╤Б╤З╨░╨╜╨╛╨╝ ╨╕╨╗╨╕ ╨│╨╗╨╕╨╜╨╕╤Б╤В╨╛╨╝ ╨│╤А╤Г╨╜╤В╨╡, ╤Е╨░╤А╨░╨║╤В╨╡╤А╨╜╨╛╨╝ ╨┤╨╗╤П ╨╝╨░╤А╤Б╨╕╨░╨╜╤Б╨║╨╛╨╣ ╨┐╨╛╨▓╨╡╤А╤Е╨╜╨╛╤Б╤В╨╕.\n\n╨д╨░╤Б╨░╨┤ ╨╝╨╛╨┤╤Г╨╗╤П ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜ ╨╕╨╖ ╨┐╤А╨╛╨╖╤А╨░╤З╨╜╨╛╨│╨╛ ╨╝╨░╤В╨╡╤А╨╕╨░╨╗╨░, ╨┐╨╛╤Е╨╛╨╢╨╡╨│╨╛ ╨╜╨░ ╤Б╤В╨╡╨║╨╗╨╛, ╤З╤В╨╛ ╨┐╨╛╨╖╨▓╨╛╨╗╤П╨╡╤В ╤Г╨▓╨╕╨┤╨╡╤В╤М ╨▓╨╜╤Г╤В╤А╨╡╨╜╨╜╨╡╨╡ ╨┐╤А	\N	\N	\N	qwen3-vl-30b-a3b	SUCCESS	\N	10826	2026-02-07 22:59:33.770575+00
86	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	╨Э╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╕ ╨┐╤А╨╡╨┤╤Б╤В╨░╨▓╨╗╨╡╨╜ ╨╗╨╛╨│╨╛╤В╨╕╨┐ ╨║╨╛╨╝╨┐╨░╨╜╨╕╨╕ ╨┐╨╛╨┤ ╨╜╨░╨╖╨▓╨░╨╜╨╕╨╡╨╝ ┬л╨Т╨Ш╨Э╨Ч╨Ю╨а┬╗. ╨Ф╨╕╨╖╨░╨╣╨╜ ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░ ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜ ╨▓ ╤Б╤В╤А╨╛╨│╨╛╨╝ ╨╕ ╨┐╤А╨╛╤Д╨╡╤Б╤Б╨╕╨╛╨╜╨░╨╗╤М╨╜╨╛╨╝ ╤Б╤В╨╕╨╗╨╡, ╨╕╤Б╨┐╨╛╨╗╤М╨╖╤Г╤П ╤Б╨╛╤З╨╡╤В╨░╨╜╨╕╨╡ ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨╛╨│╨╛ ╨╕ ╤З╨╡╤А╨╜╨╛╨│╨╛ ╤Ж╨▓╨╡╤В╨╛╨▓ ╨╜╨░ ╨▒╨╡╨╗╨╛╨╝ ╤Д╨╛╨╜╨╡.\n\n╨Ы╨╛╨│╨╛╤В╨╕╨┐ ╤Б╨╛╤Б╤В╨╛╨╕╤В ╨╕╨╖ ╨┤╨▓╤Г╤Е ╨╛╤Б╨╜╨╛╨▓╨╜╤Л╤Е ╤З╨░╤Б╤В╨╡╨╣: ╨│╤А╨░╤Д╨╕╤З╨╡╤Б╨║╨╛╨│╨╛ ╤Н╨╗╨╡╨╝╨╡╨╜╤В╨░ ╤Б╨╗╨╡╨▓╨░ ╨╕ ╤В╨╡╨║╤Б╤В╨╛╨▓╨╛╨│╨╛ ╨▒╨╗╨╛╨║╨░ ╤Б╨┐╤А╨░╨▓╨░.\n\n**╨У╤А╨░╤Д╨╕╤З╨╡╤Б╨║╨╕╨╣ ╤Н╨╗╨╡╨╝╨╡╨╜╤В:**\n- ╨д╨╛╤А╨╝╨░: ╨н╤В╨╛ ╤Й╨╕╤В, ╤Б╨╕╨╝╨▓╨╛╨╗╨╕╨╖╨╕╤А╤Г╤О╤Й╨╕╨╣ ╨╖╨░╤Й╨╕╤В╤Г, ╨╜╨░╨┤╨╡╨╢╨╜╨╛╤Б╤В╤М ╨╕ ╨▒╨╡╨╖╨╛╨┐╨░╤Б╨╜╨╛╤Б╤В╤М.\n- ╨ж╨▓╨╡╤В: ╨й╨╕╤В ╤З╨╡╤А╨╜╨╛╨│╨╛ ╤Ж╨▓╨╡╤В╨░ ╤Б ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨╛╨╣ ╨╛╨║╨░╨╜╤В╨╛╨▓╨║╨╛╨╣.\n- ╨Т╨╜╤Г╤В╤А╨╕ ╤Й╨╕╤В╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╤Л ╨┤╨▓╨░ ╨╛╤Б╨╜╨╛╨▓╨╜╤Л╤Е ╤Н╨╗╨╡╨╝╨╡╨╜╤В╨░:\n    - ╨б╨╕╨╗╤Г╤Н╤В ╨░╨▓╤В	\N	\N	\N	qwen3-vl-30b-a3b	SUCCESS	\N	17191	2026-02-07 23:22:23.859651+00
87	1	VIDEO_ANIMATE	╨░╨╜╨╕╨╝╨░╤Ж╨╕╤П ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░, ╨▒╤Г╨║╨▓╤Л ╨▓╤Л╨╡╨╖╨╢╨░╤О╤В ╨╕╨╖ ╨┐╨╛╨┤ ╤Б╨░╨╝╨╛╨│╨╛ ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░ ╤Б ╨║╤А╤Г╤В╤Л╨╝ ╨╖╨▓╤Г╨║╨╛╨╝	\N	\N	\N	\N	sora-2-all	FAILED	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 202602080722448749252614W1Dwquh)","type":"comet_api_error"}}	\N	2026-02-07 23:22:44.331669+00
88	1	TEXT	╨░╨╜╨╕╨╝╨░╤Ж╨╕╤П ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░, ╨▒╤Г╨║╨▓╤Л ╨▓╤Л╨╡╨╖╨╢╨░╤О╤В ╨╕╨╖ ╨┐╨╛╨┤ ╤Б╨░╨╝╨╛╨│╨╛ ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░ ╤Б ╨║╤А╤Г╤В╤Л╨╝ ╨╖╨▓╤Г╨║╨╛╨╝	╨з╤В╨╛╨▒╤Л ╤А╨╡╨░╨╗╨╕╨╖╨╛╨▓╨░╤В╤М ╨░╨╜╨╕╨╝╨░╤Ж╨╕╤О, ╨┐╤А╨╕ ╨║╨╛╤В╨╛╤А╨╛╨╣ ╨▒╤Г╨║╨▓╤Л ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░ ╨▓╤Л╨╡╨╖╨╢╨░╤О╤В ╨╕╨╖-╨┐╨╛╨┤ ╤Б╨░╨╝╨╛╨│╨╛ ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░ ╤Б ┬л╨║╤А╤Г╤В╨╕╨╝┬╗ ╨╖╨▓╤Г╨║╨╛╨╝, ╨╝╨╛╨╢╨╜╨╛ ╨╕╤Б╨┐╨╛╨╗╤М╨╖╨╛╨▓╨░╤В╤М **HTML + CSS + JavaScript** (╨╕╨╗╨╕ ╨▒╨╕╨▒╨╗╨╕╨╛╤В╨╡╨║╨╕ ╨▓╤А╨╛╨┤╨╡ **GSAP** ╨╕ **Web Audio API** ╨┤╨╗╤П ╨╖╨▓╤Г╨║╨░). ╨Э╨╕╨╢╨╡ тАФ ╨▒╨░╨╖╨╛╨▓╤Л╨╣ ╨┐╤А╨╕╨╝╨╡╤А.\n\n---\n\n### ЁЯОп ╨з╤В╨╛ ╨╜╤Г╨╢╨╜╨╛:\n1. ╨Ы╨╛╨│╨╛╤В╨╕╨┐ (╤В╨╡╨║╤Б╤В ╨╕╨╗╨╕ SVG).\n2. ╨Р╨╜╨╕╨╝╨░╤Ж╨╕╤П ╨┐╨╛╤П╨▓╨╗╨╡╨╜╨╕╤П ╨▒╤Г╨║╨▓ (╨╜╨░╨┐╤А╨╕╨╝╨╡╤А, ╤Б╨╗╨╡╨▓╨░/╤Б╨┐╤А╨░╨▓╨░/╤Б╨╜╨╕╨╖╤Г).\n3. ╨Ч╨▓╤Г╨║ ╨┐╤А╨╕ ╨┐╨╛╤П╨▓╨╗╨╡╨╜╨╕╨╕ ╨║╨░╨╢╨┤╨╛╨╣ ╨▒╤Г╨║╨▓╤Л.\n\n---\n\n### тЬЕ ╨Я╤А╨╕╨╝╨╡╤А ╨╜╨░ HTML/CSS/JS\n\n#### HTML\n```html\n<div class="logo-container">\n  <h1 class="logo" id="logo">LOGO	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	26559	2026-02-07 23:22:53.851787+00
89	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	╨Э╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╕ ╨┐╤А╨╡╨┤╤Б╤В╨░╨▓╨╗╨╡╨╜ ╨╗╨╛╨│╨╛╤В╨╕╨┐ ╨║╨╛╨╝╨┐╨░╨╜╨╕╨╕ ┬л╨Т╨Ш╨Э╨Ч╨╛╤А┬╗. ╨Ю╨╜ ╤Б╨╛╤Б╤В╨╛╨╕╤В ╨╕╨╖ ╨┤╨▓╤Г╤Е ╨╛╤Б╨╜╨╛╨▓╨╜╤Л╤Е ╤З╨░╤Б╤В╨╡╨╣: ╨│╤А╨░╤Д╨╕╤З╨╡╤Б╨║╨╛╨│╨╛ ╤Н╨╗╨╡╨╝╨╡╨╜╤В╨░ ╤Б╨╗╨╡╨▓╨░ ╨╕ ╤В╨╡╨║╤Б╤В╨╛╨▓╨╛╨│╨╛ ╨▒╨╗╨╛╨║╨░ ╤Б╨┐╤А╨░╨▓╨░, ╤А╨░╤Б╨┐╨╛╨╗╨╛╨╢╨╡╨╜╨╜╤Л╤Е ╨╜╨░ ╨▒╨╡╨╗╨╛╨╝ ╤Д╨╛╨╜╨╡.\n\n**╨У╤А╨░╤Д╨╕╤З╨╡╤Б╨║╨╕╨╣ ╤Н╨╗╨╡╨╝╨╡╨╜╤В:**\n- ╨н╤В╨╛ ╤Й╨╕╤В ╤Б ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨╛╨╣ ╨╛╨║╨░╨╜╤В╨╛╨▓╨║╨╛╨╣ ╨╕ ╤З╨╡╤А╨╜╤Л╨╝ ╤Д╨╛╨╜╨╛╨╝.\n- ╨Т╨╜╤Г╤В╤А╨╕ ╤Й╨╕╤В╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨░ ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨░╤П ╤Б╨╕╨╗╤Г╤Н╤В╨╜╨░╤П ╤Д╨╕╨│╤Г╤А╨░ ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╤П.\n- ╨Я╨╡╤А╨╡╨┤ ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╨╡╨╝ ╨╜╨░╤Е╨╛╨┤╨╕╤В╤Б╤П ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨░╤П ╨╗╤Г╨┐╨░, ╤Б╨╕╨╝╨▓╨╛╨╗╨╕╨╖╨╕╤А╤Г╤О╤Й╨░╤П ╤В╤Й╨░╤В╨╡╨╗╤М╨╜╤Л╨╣ ╨╛╤Б╨╝╨╛╤В╤А.\n- ╨Т ╤Ж╨╡╨╜╤В╤А╨╡ ╨╗╤Г╨┐╤Л ╨╜╨░╤Е╨╛╨┤╨╕╤В╤Б╤П ╨║╤А╨░╤Б╨╜╤Л╨╣ ╨│╨░╨╗╨╛╤З╨║╨░, ╤Г╨║╨░╨╖╤Л╨▓╨░╤О╤Й╨░╤П ╨╜╨░ ╤Г╤Б╨┐╨╡╤И╨╜╨╛╨╡ ╨╖╨░╨▓╨╡╤А╤И╨╡╨╜╨╕╨╡ ╨┐╤А╨╛╨▓╨╡╤А╨║╨╕.\n- ╨Ю╨▒╤Й╨╕╨╣ ╨┤╨╕╨╖╨░╨╣╨╜ 	\N	\N	\N	qwen3-vl-30b-a3b	SUCCESS	\N	15544	2026-02-07 23:23:37.220146+00
90	1	VIDEO_ANIMATE	╨░╨╜╨╕╨╝╨░╤Ж╨╕╤П ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░, ╨▒╤Г╨║╨▓╤Л ╨▓╤Л╨╡╨╖╨╢╨░╤О╤В ╨╕╨╖ ╨┐╨╛╨┤ ╤Б╨░╨╝╨╛╨│╨╛ ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░ ╤Б ╨║╤А╤Г╤В╤Л╨╝ ╨╖╨▓╤Г╨║╨╛╨╝	\N	\N	\N	\N	sora-2-all	FAILED	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 20260208072356156301933ZtXHp2s0)","type":"comet_api_error"}}	\N	2026-02-07 23:23:55.583478+00
91	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	╨Э╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╕ ╨┐╤А╨╡╨┤╤Б╤В╨░╨▓╨╗╨╡╨╜ ╨╗╨╛╨│╨╛╤В╨╕╨┐ ╨║╨╛╨╝╨┐╨░╨╜╨╕╨╕ ╨╕╨╗╨╕ ╤Б╨╡╤А╨▓╨╕╤Б╨░ ╨┐╨╛╨┤ ╨╜╨░╨╖╨▓╨░╨╜╨╕╨╡╨╝ ┬л╨Т╨Ш╨Э╨Ч╨╛╤А┬╗. ╨Ю╨╜ ╤Б╨╛╤Б╤В╨╛╨╕╤В ╨╕╨╖ ╨┤╨▓╤Г╤Е ╨╛╤Б╨╜╨╛╨▓╨╜╤Л╤Е ╤З╨░╤Б╤В╨╡╨╣: ╨│╤А╨░╤Д╨╕╤З╨╡╤Б╨║╨╛╨│╨╛ ╤Н╨╗╨╡╨╝╨╡╨╜╤В╨░ ╤Б╨╗╨╡╨▓╨░ ╨╕ ╤В╨╡╨║╤Б╤В╨░ ╤Б╨┐╤А╨░╨▓╨░, ╤А╨░╤Б╨┐╨╛╨╗╨╛╨╢╨╡╨╜╨╜╤Л╤Е ╨╜╨░ ╨▒╨╡╨╗╨╛╨╝ ╤Д╨╛╨╜╨╡.\n\n**╨У╤А╨░╤Д╨╕╤З╨╡╤Б╨║╨╕╨╣ ╤Н╨╗╨╡╨╝╨╡╨╜╤В (╤Б╨╗╨╡╨▓╨░):**\n- ╨н╤В╨╛ ╤Н╨╝╨▒╨╗╨╡╨╝╨░ ╨▓ ╤Д╨╛╤А╨╝╨╡ ╤Й╨╕╤В╨░ ╤Б ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨╛╨╣ ╨╛╨║╨░╨╜╤В╨╛╨▓╨║╨╛╨╣ ╨╕ ╤З╨╡╤А╨╜╤Л╨╝ ╤Д╨╛╨╜╨╛╨╝.\n- ╨Т╨╜╤Г╤В╤А╨╕ ╤Й╨╕╤В╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨░ ╤Б╤В╨╕╨╗╨╕╨╖╨╛╨▓╨░╨╜╨╜╨░╤П ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨░╤П ╤Б╨╕╨╗╤Г╤Н╤В╨╜╨░╤П ╤Д╨╕╨│╤Г╤А╨░ ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╤П, ╨▓╨╕╨┤ ╤Б╨┐╨╡╤А╨╡╨┤╨╕.\n- ╨Я╨╡╤А╨╡╨┤ ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╨╡╨╝ ╨╜╨░╤Е╨╛╨┤╨╕╤В╤Б╤П ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨╛╨╡ ╤Г╨▓╨╡╨╗╨╕╤З╨╕╤В╨╡╨╗╤М╨╜╨╛╨╡ ╤Б╤В╨╡╨║╨╗╨╛ (╨╗╤Г╨┐╨░), ╨║╨╛╤В╨╛╤А╨╛╨╡ ╨╜╨░╨║╨╗╨░╨┤╤Л╨▓╨░╨╡╤В╤Б╤П ╨╜╨░ ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╤М.\n- ╨Т╨╜╤Г╤В╤А╨╕ 	\N	\N	\N	qwen3-vl-30b-a3b	SUCCESS	\N	8157	2026-02-07 23:49:45.474203+00
92	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	╨Э╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╕ ╨┐╤А╨╡╨┤╤Б╤В╨░╨▓╨╗╨╡╨╜ ╨╗╨╛╨│╨╛╤В╨╕╨┐ ╨║╨╛╨╝╨┐╨░╨╜╨╕╨╕ ╨╕╨╗╨╕ ╤Б╨╡╤А╨▓╨╕╤Б╨░ ╨┐╨╛╨┤ ╨╜╨░╨╖╨▓╨░╨╜╨╕╨╡╨╝ ┬л╨Т╨Ш╨Э╨Ч╨╛╤А┬╗. ╨Ф╨╕╨╖╨░╨╣╨╜ ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░ ╨▓╨║╨╗╤О╤З╨░╨╡╤В ╨▓ ╤Б╨╡╨▒╤П ╨╜╨╡╤Б╨║╨╛╨╗╤М╨║╨╛ ╨║╨╗╤О╤З╨╡╨▓╤Л╤Е ╤Н╨╗╨╡╨╝╨╡╨╜╤В╨╛╨▓:\n\n- **╨Ы╨╡╨▓╨░╤П ╤З╨░╤Б╤В╤М ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░:** ╨Ш╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨░ ╤Н╨╝╨▒╨╗╨╡╨╝╨░ ╨▓ ╨▓╨╕╨┤╨╡ ╤Й╨╕╤В╨░ ╤Б ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨╛╨╣ ╨╛╨║╨░╨╜╤В╨╛╨▓╨║╨╛╨╣ ╨╕ ╤З╨╡╤А╨╜╤Л╨╝ ╤Д╨╛╨╜╨╛╨╝. ╨Т╨╜╤Г╤В╤А╨╕ ╤Й╨╕╤В╨░ ╨╜╨░╤Е╨╛╨┤╨╕╤В╤Б╤П ╤Б╤В╨╕╨╗╨╕╨╖╨╛╨▓╨░╨╜╨╜╨╛╨╡ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡ ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╤П, ╨▓╨╕╨┤ ╤Б╨┐╨╡╤А╨╡╨┤╨╕, ╤В╨░╨║╨╢╨╡ ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜╨╜╨╛╨│╨╛ ╨▓ ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨╛╨╝ ╤Ж╨▓╨╡╤В╨╡. ╨Я╨╡╤А╨╡╨┤ ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╨╡╨╝ ╨╜╨░╤Е╨╛╨┤╨╕╤В╤Б╤П ╤Г╨▓╨╡╨╗╨╕╤З╨╕╤В╨╡╨╗╤М╨╜╨╛╨╡ ╤Б╤В╨╡╨║╨╗╨╛ (╨╗╤Г╨┐╨░), ╨▓ ╤Ж╨╡╨╜╤В╤А╨╡ ╨║╨╛╤В╨╛╤А╨╛╨│╨╛ ╨╜╨░╤Е╨╛╨┤╨╕╤В╤Б╤П ╨║╤А╨░╤Б╨╜╨░╤П ╨│╨░╨╗╨╛╤З╨║╨░, ╤Б╨╕╨╝╨▓╨╛╨╗╨╕╨╖╨╕╤А╤Г╤О╤Й╨░╤П ╨┐╤А╨╛╨▓╨╡╤А╨║╤Г, ╨╛╨┤╨╛╨▒╤А╨╡╨╜╨╕╨╡ ╨╕╨╗╨╕ ╨┐╨╛╨┤	\N	\N	\N	qwen3-vl-30b-a3b	SUCCESS	\N	8879	2026-02-07 23:49:46.380932+00
93	1	VIDEO_ANIMATE	╨░╨╜╨╕╨╝╨╕╤А╨╛╨▓╨░╤В╤М ╨╗╨╛╨│╨╛╤В╨╕╨┐ ╨┤╨░╨▒╤Л ╨▒╤Г╨║╨▓╤Л ╨▓╤Л╨╡╨╖╨░╨╗╨╕ ╨╕╨╖ ╨╜╨╡╨│╨╛	\N	\N	\N	\N	sora-2	SUCCESS	\N	\N	2026-02-07 23:51:28.077108+00
94	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	\N	\N	\N	\N	gpt-4o-vision	FAILED	Telegram server says - Bad Request: BUTTON_DATA_INVALID	5985	2026-02-07 23:54:59.89418+00
95	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	\N	\N	\N	\N	gpt-4o-vision	FAILED	Telegram server says - Bad Request: BUTTON_DATA_INVALID	11715	2026-02-07 23:59:54.008854+00
114	3	IMAGE	╨░╤А╨▒╤Г╨╖ ╨▓ ╤И╤В╨░╨╜╨░╤Е	\N	\N	\N	0.040000	dall-e-3	SUCCESS	\N	\N	2026-02-09 14:13:53.720762+00
120	3	IMAGE	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╨░╤А╨▒╤Г╨╖ ╤Б ╤Б╨╕╤Б╤М╨║╨░╨╝╨╕ ╨▓ ╤И╤В╨░╨╜╨░╤Е	\N	\N	\N	0.040000	dall-e-3	SUCCESS	\N	\N	2026-02-09 14:16:23.925136+00
96	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	╨Э╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╕ ╨┐╤А╨╡╨┤╤Б╤В╨░╨▓╨╗╨╡╨╜ ╨╗╨╛╨│╨╛╤В╨╕╨┐ ╨╕ ╤Б╨╗╨╛╨│╨░╨╜ ╨║╨╛╨╝╨┐╨░╨╜╨╕╨╕. ╨Ф╨░╨▓╨░╨╣╤В╨╡ ╤А╨░╤Б╤Б╨╝╨╛╤В╤А╨╕╨╝ ╨╡╨│╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛:\n\n- **╨Ю╤Б╨╜╨╛╨▓╨╜╨╛╨╣ ╤Н╨╗╨╡╨╝╨╡╨╜╤В**: ╨б╨╗╨╡╨▓╨░ ╨╜╨░╤Е╨╛╨┤╨╕╤В╤Б╤П ╤Н╨╝╨▒╨╗╨╡╨╝╨░ ╨▓ ╨▓╨╕╨┤╨╡ ╤Й╨╕╤В╨░ ╤Б ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨╛╨╣ ╨╛╨║╨░╨╜╤В╨╛╨▓╨║╨╛╨╣ ╨╜╨░ ╤З╨╡╤А╨╜╨╛╨╝ ╤Д╨╛╨╜╨╡. ╨й╨╕╤В ╤Б╨╕╨╝╨▓╨╛╨╗╨╕╨╖╨╕╤А╤Г╨╡╤В ╨╖╨░╤Й╨╕╤В╤Г ╨╕ ╨╜╨░╨┤╨╡╨╢╨╜╨╛╤Б╤В╤М.\n\n- **╨Ш╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╤П ╨▓ ╤Н╨╝╨▒╨╗╨╡╨╝╨╡**:\n    - ╨Т╨╜╤Г╤В╤А╨╕ ╤Й╨╕╤В╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜ ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╤Л╨╣ ╤Б╨╕╨╗╤Г╤Н╤В ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╤П, ╨▓╨╕╨┤ ╤Б╨┐╨╡╤А╨╡╨┤╨╕.\n    - ╨Я╨╡╤А╨╡╨┤ ╨░╨▓╤В╨╛╨╝╨╛╨▒╨╕╨╗╨╡╨╝ ╨╜╨░╤Е╨╛╨┤╨╕╤В╤Б╤П ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨╛╨╡ ╤Г╨▓╨╡╨╗╨╕╤З╨╕╤В╨╡╨╗╤М╨╜╨╛╨╡ ╤Б╤В╨╡╨║╨╗╨╛ (╨╗╤Г╨┐╨░).\n    - ╨Т╨╜╤Г╤В╤А╨╕ ╨╗╤Г╨┐╤Л ╨╜╨░╤Е╨╛╨┤╨╕╤В╤Б╤П ╨║╤А╨░╤Б╨╜╨░╤П ╨│╨░╨╗╨╛╤З╨║╨░ (╨┐╤А╨╛╨▓╨╡╤А╨║╨░), ╤З╤В╨╛ ╤Г╨║╨░╨╖╤Л╨▓╨░╨╡╤В ╨╜╨░ ╤Г╤Б╨┐╨╡╤И╨╜╤Г╤О ╨┐╤А╨╛╨▓╨╡╤А╨║╤Г.\n\n- **	\N	\N	\N	qwen3-vl-30b-a3b	SUCCESS	\N	12112	2026-02-08 00:00:50.255025+00
97	1	VIDEO	╨░╨╜╨╕╨╝╨╕╤А╨╛╨▓╨░╤В╤М ╨╗╨╛╨│╨╛╤В╨╕╨┐ ╨┤╨░╨▒╤Л ╨▒╤Г╨║╨▓╤Л ╨▓╤Л╨╡╨╖╨░╨╗╨╕ ╨╕╨╖ ╨╜╨╡╨│╨╛	\N	\N	\N	\N	sora-2	FAILED	Video generation failed: Your request was blocked by our moderation system.	\N	2026-02-08 00:05:11.306621+00
98	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	╨Э╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╕ ╨┐╤А╨╡╨┤╤Б╤В╨░╨▓╨╗╨╡╨╜ ╨╗╨╛╨│╨╛╤В╨╕╨┐ ╨║╨╛╨╝╨┐╨░╨╜╨╕╨╕ ╨╕╨╗╨╕ ╤Б╨╡╤А╨▓╨╕╤Б╨░ ╨┐╨╛╨┤ ╨╜╨░╨╖╨▓╨░╨╜╨╕╨╡╨╝ ┬л╨Т╨Ш╨Э╨Ч╨╛╤А┬╗. ╨Ф╨╕╨╖╨░╨╣╨╜ ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░ ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜ ╨▓ ╤Б╤В╤А╨╛╨│╨╛╨╝ ╨╕ ╨┐╤А╨╛╤Д╨╡╤Б╤Б╨╕╨╛╨╜╨░╨╗╤М╨╜╨╛╨╝ ╤Б╤В╨╕╨╗╨╡, ╨╕╤Б╨┐╨╛╨╗╤М╨╖╤Г╤П ╤Б╨╛╤З╨╡╤В╨░╨╜╨╕╨╡ ╤З╨╡╤А╨╜╨╛╨│╨╛, ╨╖╨╛╨╗╨╛╤В╨╛╨│╨╛ ╨╕ ╤В╨╡╨╝╨╜╨╛-╤Б╨╡╤А╨╛╨│╨╛ ╤Ж╨▓╨╡╤В╨╛╨▓ ╨╜╨░ ╨▒╨╡╨╗╨╛╨╝ ╤Д╨╛╨╜╨╡.\n\n╨Ы╨╛╨│╨╛╤В╨╕╨┐ ╤Б╨╛╤Б╤В╨╛╨╕╤В ╨╕╨╖ ╨┤╨▓╤Г╤Е ╨╛╤Б╨╜╨╛╨▓╨╜╤Л╤Е ╤З╨░╤Б╤В╨╡╨╣: ╨│╤А╨░╤Д╨╕╤З╨╡╤Б╨║╨╛╨│╨╛ ╤Н╨╗╨╡╨╝╨╡╨╜╤В╨░ ╤Б╨╗╨╡╨▓╨░ ╨╕ ╤В╨╡╨║╤Б╤В╨╛╨▓╨╛╨╣ ╤З╨░╤Б╤В╨╕ ╤Б╨┐╤А╨░╨▓╨░.\n\n**╨У╤А╨░╤Д╨╕╤З╨╡╤Б╨║╨╕╨╣ ╤Н╨╗╨╡╨╝╨╡╨╜╤В (╤Б╨╗╨╡╨▓╨░):**\n- ╨н╤В╨╛ ╤Й╨╕╤В ╤Б ╨╖╨╛╨╗╨╛╤В╨╛╨╣ ╨╛╨║╨░╨╜╤В╨╛╨▓╨║╨╛╨╣ ╨╕ ╤З╨╡╤А╨╜╤Л╨╝ ╤Д╨╛╨╜╨╛╨╝, ╤З╤В╨╛ ╤Б╨╕╨╝╨▓╨╛╨╗╨╕╨╖╨╕╤А╤Г╨╡╤В ╨╖╨░╤Й╨╕╤В╤Г, ╨╜╨░╨┤╨╡╨╢╨╜╨╛╤Б╤В╤М ╨╕ ╨▒╨╡╨╖╨╛╨┐╨░╤Б╨╜╨╛╤Б╤В╤М.\n- ╨Т╨╜╤Г╤В╤А╨╕ ╤Й╨╕╤В╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨░ ╨╖╨╛╨╗╨╛╤В╨░╤П ╤Б╨╕╨╗╤Г╤Н╤В╨╜╨░╤П ╤Д╨╕╨│╤Г╤А╨░ ╨░╨▓╤В╨╛	\N	\N	\N	qwen3-vl-30b-a3b	SUCCESS	\N	19510	2026-02-08 00:06:32.900362+00
99	1	VIDEO	Logo animation with letters emerging from under the image	\N	\N	\N	\N	sora-2	SUCCESS	\N	\N	2026-02-08 00:08:12.589325+00
100	1	TEXT	╨║╤Г	╨Я╤А╨╕╨▓╨╡╤В! ╨з╨╡╨╝ ╨╝╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М?	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	3793	2026-02-08 00:20:54.388503+00
101	1	LONG_VIDEO	╨Ъ╨╛╤Б╨╝╨╕╤З╨╡╤Б╨║╨╕╨╣ ╨║╨╛╤А╨░╨▒╨╗╤М ╨┐╤А╨╛╨╗╨╡╤В╨░╨╡╤В ╤З╨╡╤А╨╡╨╖ ╨┐╨╛╤П╤Б ╨░╤Б╤В╨╡╤А╨╛╨╕╨┤╨╛╨▓ ╨╕ ╨┐╤А╨╕╨▒╨╗╨╕╨╢╨░╨╡╤В╤Б╤П ╨║ ╨┐╨╗╨░╨╜╨╡╤В╨╡ ╤Б ╨║╨╛╨╗╤М╤Ж╨░╨╝╨╕	\N	\N	\N	\N	sora-2	FAILED	CometAPI video creation failed: 403 - {"code":null,"message":"user quota is not enough"}	\N	2026-02-08 01:59:00.857392+00
102	1	IMAGE	╨Ю╨┐╨╕╤И╨╕ ╤З╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛ ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛	╨Э╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╕ ╨┐╤А╨╡╨┤╤Б╤В╨░╨▓╨╗╨╡╨╜ ╨╗╨╛╨│╨╛╤В╨╕╨┐ ╨║╨╛╨╝╨┐╨░╨╜╨╕╨╕ ╨╕╨╗╨╕ ╤Б╨╡╤А╨▓╨╕╤Б╨░ ╨┐╨╛╨┤ ╨╜╨░╨╖╨▓╨░╨╜╨╕╨╡╨╝ ┬л╨Т╨Ш╨Э╨Ч╨╛╤А┬╗. ╨Ф╨╕╨╖╨░╨╣╨╜ ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░ ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜ ╨▓ ╤Б╨╛╨▓╤А╨╡╨╝╨╡╨╜╨╜╨╛╨╝ ╤Б╤В╨╕╨╗╨╡ ╤Б ╨╕╤Б╨┐╨╛╨╗╤М╨╖╨╛╨▓╨░╨╜╨╕╨╡╨╝ ╤З╤С╤В╨║╨╕╤Е ╤Д╨╛╤А╨╝ ╨╕ ╨║╨╛╨╜╤В╤А╨░╤Б╤В╨╜╤Л╤Е ╤Ж╨▓╨╡╤В╨╛╨▓.\n\n╨Т╨╛╤В ╨┐╨╛╨┤╤А╨╛╨▒╨╜╨╛╨╡ ╨╛╨┐╨╕╤Б╨░╨╜╨╕╨╡ ╨║╨╛╨╝╨┐╨╛╨╜╨╡╨╜╤В╨╛╨▓ ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░:\n\n- **╨Ю╤Б╨╜╨╛╨▓╨╜╨╛╨╣ ╤Н╨╗╨╡╨╝╨╡╨╜╤В (╤Б╨╗╨╡╨▓╨░):** ╨н╤В╨╛ ╨│╤А╨░╤Д╨╕╤З╨╡╤Б╨║╨╕╨╣ ╨╖╨╜╨░╨║ ╨▓ ╤Д╨╛╤А╨╝╨╡ ╤Й╨╕╤В╨░, ╨║╨╛╤В╨╛╤А╤Л╨╣ ╤Б╨╕╨╝╨▓╨╛╨╗╨╕╨╖╨╕╤А╤Г╨╡╤В ╨╖╨░╤Й╨╕╤В╤Г, ╨▒╨╡╨╖╨╛╨┐╨░╤Б╨╜╨╛╤Б╤В╤М ╨╕ ╨╜╨░╨┤╤С╨╢╨╜╨╛╤Б╤В╤М.\n    - **╨ж╨▓╨╡╤В:** ╨й╨╕╤В ╤З╤С╤А╨╜╨╛╨│╨╛ ╤Ж╨▓╨╡╤В╨░ ╤Б ╤В╨╛╨╜╨║╨╛╨╣ ╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨╛╨╣ (╨╖╨╛╨╗╨╛╤В╨╕╤Б╤В╨╛-╨║╨╛╤А╨╕╤З╨╜╨╡╨▓╨╛╨╣) ╤А╨░╨╝╨║╨╛╨╣.\n    - **╨Ш╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╡ ╨▓╨╜╤Г╤В╤А╨╕ ╤Й╨╕╤В╨░:** ╨Э╨░ ╤З╤С╤А╨╜╨╛╨╝ ╤Д╨╛╨╜╨╡ ╤Й╨╕╤В╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╤С╨╜ ╤Б╨╕╨╗	\N	\N	\N	qwen3-vl-30b-a3b	SUCCESS	\N	11699	2026-02-08 03:33:27.730331+00
103	1	VIDEO_ANIMATE	╨░╨╜╨╕╨╝╨░╤Ж╨╕╤П ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░ ╨║╨░╨║ ╨▒╤Г╨║╨▓╤Л ╨║╤А╨░╤Б╨╕╨▓╨╛ ╨▓╤Л╨╗╨╡╨╖╨░╤О╤В ╨╕╨╖ ╨┐╨╛╨┤ ╨║╨░╤А╤В╨╕╨╜╨║╨╕ ╨╕ ╨╜╨░╨╛╨▒╨╛╤А╨╛╤В	\N	\N	\N	\N	sora-2	SUCCESS	\N	\N	2026-02-08 03:36:04.102922+00
104	1	LONG_VIDEO	╨Ъ╨╛╤Б╨╝╨╕╤З╨╡╤Б╨║╨╕╨╣ ╨║╨╛╤А╨░╨▒╨╗╤М ╨┐╤А╨╛╨╗╨╡╤В╨░╨╡╤В ╤З╨╡╤А╨╡╨╖ ╨┐╨╛╤П╤Б ╨░╤Б╤В╨╡╤А╨╛╨╕╨┤╨╛╨▓ ╨╕ ╨┐╤А╨╕╨▒╨╗╨╕╨╢╨░╨╡╤В╤Б╤П ╨║ ╨┐╨╗╨░╨╜╨╡╤В╨╡ ╤Б ╨║╨╛╨╗╤М╤Ж╨░╨╝╨╕	\N	\N	\N	\N	sora-2	SUCCESS	\N	\N	2026-02-08 03:47:51.255543+00
105	2	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╨║╤Г	╨Ъ╤Г! ╨Ъ╨░╨║ ╨┤╨╡╨╗╨░? ╨з╨╡╨╝ ╨╝╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М?	\N	\N	0.000204	qwen3-max-2026-01-23	SUCCESS	\N	\N	2026-02-08 03:52:48.760596+00
106	2	IMAGE	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╤Б╨┤╨╡╨╗╨░╨╣ ╤Д╨╛╤В╨╛ ╨╝╨╡╨╜╤П (╤П ╤А╤Г╤Б╤Б╨║╨╕╨╣)	\N	\N	\N	0.040000	dall-e-3	SUCCESS	\N	\N	2026-02-08 03:53:15.273544+00
107	1	VOICE	\N	\N	\N	\N	\N	unknown	FAILED	Connection error.	\N	2026-02-09 12:39:13.798849+00
108	1	VOICE	\N	╨Э╨╡╨╝╨╜╨╛╨│╨╛ ╤А╨░╤Б╤Б╨║╨░╨╢╤Г, ╨║╨░╨║ ╤П ╤А╨░╨▒╨╛╤В╨░╤О. ╨г ╨╝╨╡╨╜╤П ╨╡╤Б╤В╤М ╨║╨╗╨╕╨╡╨╜╤В╤Л, ╤П ╨╕╨╜╤В╨╡╨│╤А╨░╤В╨╛╤А, ╤П ╨╛╨▒╨╡╤Б╨┐╨╡╤З╨╕╨▓╨░╤О ╨▓╤Б╤П╨║╨╕╨╡ ╤Г╤Б╨╗╤Г╨│╨╕ ╨┐╨╛ AMSRM, ╨╕ ╨╛╨▒╤Л╤З╨╜╨╛ ╨╕╨╜╨╛╨│╨┤╨░ ╤Г ╨╜╨╕╤Е ╨╡╤Б╤В╤М ╨╖╨░╨┐╤А╨╛╤Б╤Л ╨╜╨░ ╤А╨░╨╖╤А╨░╨▒╨╛╤В╨║╤Г, ╨╕ ╤П ╨╡╤Й╨╡ ╤А╨░╨╖╤А╨░╨▒╨╛╤В╤З╨╕╨║, ╨║╨╛╤В╨╛╤А╤Л╨╣ ╨╝╨╛╨╢╨╡╤В ╤А╨╡╤И╨░╤В╤М ╨╜╨╡╨║╨╛╤В╨╛╤А╤Л╨╡ ╨╖╨░╨┤╨░╤З╨╕. ╨Ъ╨░╨║ ╤Н╤В╨╛ ╤А╨░╨▒╨╛╤В╨░╨╡╤В? ╨Ь╨╜╨╡ ╤В╨░╨╝ ╨╖╨░╨║╨░╨╖╤З╨╕╨║ ╤Б╨┐╤А╨░╤И╨╕╨▓╨░╨╡╤В, ╨▓╨╛╤В ╤В╨░╨║╨╛╨╡ ╤Е╨╛╤З╤Г, ╨╕╨╗╨╕ ╨╛╨╜ ╨│╨╛╨▓╨╛╤А╨╕╤В, ╤З╤В╨╛ ╤Г ╨╜╨╡╨│╨╛ ╨╖╨┤╨╡╤Б╤М ╨▒╨╛╨╗╨╕╤В, ╤П ╨╡╨╝╤Г ╨┐╤А╨╡╨┤╨╗╨░╨│╨░╤О, ╤З╤В╨╛ ╨╝╨╛╨╢╨╜╨╛ ╨▓╨╛╤В ╤В╨░╨║ ╨▓╨╛╤В ╨░╨▓╤В╨╛╨╝╨░╤В╨╕╨╖╨╕╤А╨╛╨▓╨░╤В╤М, ╤Б╨╛╨▒╨╕╤А╨░╤О ╨╖╨░╨┤╨░╤З╤Г, ╨┐╤А╨╕╤Е╨╛╨╢╤Г ╨║ ╨▓╨░╨╝, ╨│╨╛╨▓╨╛╤А╤О, ╤З╤В╨╛ ╨▓╨╛╤В ╤В╨░╨║╨░╤П-╤В╨╛ ╨╖╨░╨┤╨░╤З╨░, ╨╝╨╜╨╡ ╨╜╤Г╨╢╨╜╨░ ╨╛╤Ж╨╡╨╜╨║╨░ ╨┐╨╛ ╤Б╤В╨╛╨╕╨╝╨╛╤Б╤В╨╕ ╨╕ ╤Б╤А╨╛╨║╨░╨╝, ╤П, ╨│╤А╤Г╨▒╨╛ ╨│╨╛╨▓╨╛╤А╤П, ╨║╨░╨║	\N	\N	0.001841	whisper-1	SUCCESS	\N	\N	2026-02-09 12:40:37.960727+00
109	1	VOICE	\N	╨Э╨░╨┐╤А╨╕╨╝╨╡╤А, Google ╤В╨░╨▒╨╗╨╕╤Ж╨░, ╨╕╨╜╤Д╤А╨░╤Б╤В╤А╤Г╨║╤В╤Г╤А╨░ ╨┤╨╛╨╗╨╢╨╜╨░ ╨▒╤Л╤В╤М ╨┐╨╛╤Б╤В╤А╨╛╨╡╨╜╨░ ╨╜╨░ ╨┐╤А╨╛╤Б╤В╨╛ Google ╤Б╨║╤А╨╕╨┐╤В╨░╤Е. ╨Я╨╛╨╗╤Г╤З╨░╨╡╤В╤Б╤П, ╤З╤В╨╛ ╤З╨╡╨╗╨╛╨▓╨╡╨║ ╨▓╨╜╤Г╤В╤А╨╕ Google ╤В╨░╨▒╨╗╨╕╤Ж╤Л ╨▓╤Л╨▒╨╕╤А╨░╨╡╤В ╨▓╨╛╤А╨╛╨╜╨║╤Г ╨▓ AMSRM ╨╕ ╨┤╨░╤В╤Л, ╤Б ╨║╨░╨║╨╛╨│╨╛ ╨┐╨╡╤А╨╕╨╛╨┤╨░, ╨┐╨╛ ╨║╨░╨║╨╛╨╣ ╨┐╨╡╤А╨╕╨╛╨┤. ╨Я╨╛╤Б╨╗╨╡ ╤Н╤В╨╛╨│╨╛ ╨╡╨│╨╛ ╨║╨╜╨╛╨┐╨║╤Г ╨╜╨░╨╢╨╕╨╝╨░╨╡╤В, ╤Г ╨╜╨╡╨│╨╛, ╨╕╨╗╨╕ ╨╝╨╛╨╢╨╜╨╛ ╤Б╤А╨░╨╖╤Г ╨┐╤А╨╛╤Б╤В╨╛ ╤В╤А╨╕╨│╨│╨╡╤А ╨┐╨╛╤Б╤В╨░╨▓╨╕╤В╤М ╨╜╨░ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╨╡ ╨▓╤В╨╛╤А╨╛╨│╨╛ ╨┐╨╛╨╗╤П ╨┤╨░╤В╤Л, ╤Г ╨╜╨╡╨│╨╛ ╨┐╨╛╨╗╤Г╤З╨░╤О╤В╤Б╤П ╨▓╤Б╨╡ ╤Б╨┤╨╡╨╗╨║╨╕ ╨╖╨░ ╤Н╤В╨╛╤В ╨┐╨╡╤А╨╕╨╛╨┤, ╨╕ ╨╕╨╖ ╨┤╨░╨╜╨╜╨╛╨╣ ╨▓╨╛╤А╨╛╨╜╨║╨╕ ╨▓╤Л╨│╤А╤Г╨╢╨░╤О╤В╤Б╤П ╨▓ ╤В╨░╨▒╨╗╨╕╤Ж╤Г Excel, ╨┐╤А╨╛╤Б╤В╨╛ ╨▓╤Б╨╡ ╨┐╨╛╨╗╤П.	\N	\N	0.001423	whisper-1	SUCCESS	\N	\N	2026-02-09 12:40:40.610796+00
110	1	VOICE	\N	╨Ю╤А╨╕╨╡╨╜╤В╨╕╤А╨╛╨▓╨░╤В╤М╤Б╤П ╤В╨░╨╝ ╨╜╨╡╤Б╨╗╨╛╨╢╨╜╨╛, ╨╕╨╖ ╤З╤В╨╛ ╤П ╤В╨░╨╝ ╨┤╨░╨╢╨╡ ╨╝╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М, ╤Г ╨╝╨╡╨╜╤П ╨╡╤Б╤В╤М ╨┐╤А╨╕╨╝╨╡╤А, ╨┐╤А╤П╨╝ ╨┤╤А╤Г╨│╨╛╨╣ ╤Б╨║╤А╨╕╨┐╤В, ╨║╨╛╤В╨╛╤А╤Л╨╣ ╤В╨╛╨╢╨╡ ╤А╨░╨╖╤К╨╡╨╝ ╨┤╨╡╨╣╤Б╤В╨▓╨╕╤П ╨╗╨╕╤Ж╨░, ╨╝╨╛╨╢╨╜╨╛ ╨┐╨╛ ╨╜╨╡╨╝╤Г ╤В╨╛╨╢╨╡ ╨┐╨╛╤Б╨╝╨╛╤В╤А╨╡╤В╤М, ╨▓╨╛╤В, ╨┐╨╛ ╨▒╤О╨┤╨╢╨╡╤В╤Г ╨║╨░╨║ ╤А╨░╨╖ ╨▓╨╛╤В ╤Г ╨▓╨░╤Б ╤Е╨╛╤В╨╡╨╗ ╤Б╨╛╤А╨╕╨╡╨╜╤В╨╕╤А╨╛╨▓╨░╤В╤М, ╨┐╨╛ ╨╖╨░╨║╨░╨╖╤Г, ╤В╨░╨╝ ╨║╨╗╨╕╨╡╨╜╤В ╨┐╤А╨╛╤Б╤В╨╛ ╨╡╤Й╨╡ ╨┤╤Г╨╝╨░╨╡╤В, ╨╛╨╜ ╤Б╨╛╨│╨╗╨░╤Б╨╛╨▓╤Л╨▓╨░╨╡╤В ╤В╨░╨╝ ╤Б ╤А╤Г╨║╨╛╨▓╨╛╨┤╨╕╤В╨╡╨╗╤П╨╝╨╕, ╨┐╨╛╤Н╤В╨╛╨╝╤Г ╤В╨░╨╝ ╤В╨╛╤З╨╜╨╛ ╤Б╨║╨░╨╖╨░╤В╤М ╨╜╨╡ ╨╝╨╛╨│╤Г, ╨▓╨╛╤В, ╨┐╨╛ ╤Б╤А╨╛╨║╨░╨╝ ╨╕╨╝╨╡╨╜╨╜╨╛.	\N	\N	0.000881	whisper-1	SUCCESS	\N	\N	2026-02-09 12:51:15.897207+00
111	1	VOICE	\N	╨Я╨╛ ╨░╨▓╤В╨╛╤А╨╕╨╖╨░╤Ж╨╕╨╕ ╤Г ╨Р╨Ь╨Р ╨┤╨▓╨░ ╨╝╨╡╤В╨╛╨┤╨░ ╨╡╤Б╤В╤М. ╨Х╤Б╤В╤М ╤А╨╡╤Д╤А╨╡╤И ╤В╨╛╨║╨╡╨╜, ╨╛╨╜ ╨▒╨╛╨╗╨╡╨╡ ╨╝╤Г╤В╨╛╤А╨╜╤Л╨╣, ╨╜╨╛ ╨╡╨│╨╛ ╨▓ ╨╜╨░╤И╨╡╨╝ ╤Б╨╗╤Г╤З╨░╨╡ ╨╜╨╡ ╨┐╨╛╨╗╤Г╤З╨╕╤В╤Б╤П ╨┐╤А╨╕╨╝╨╡╨╜╨╕╤В╤М, ╨┐╨╛╤В╨╛╨╝╤Г ╤З╤В╨╛ ╤Г ╨╜╨░╤Б ╨│╤Г╨│╨╗ ╤В╨░╨▒╨╗╨╕╤Ж, ╤В╨░╨╝ ╨╛╨╜ ╨╜╨╡ ╨▒╤Г╨┤╨╡╤В ╨╜╨╛╤А╨╝╨░╨╗╤М╨╜╨╛ ╤А╨╡╤Д╤А╨╡╤И╨╕╤В╤М╤Б╤П. ╨Х╤Б╤В╤М ╨┤╨╛╨╗╨│╨╛╤Б╤А╨╛╤З╨╜╤Л╨╣ ╤В╨╛╨║╨╡╨╜, ╨╜╨╛ ╤Н╤В╨╛ ╨┐╤А╨╛╤Б╤В╨╛ ╨┤╨╡╤Д╨╛╨╗╤В╨╜╨░╤П API ╨╕╤Б╤В╨╛╤А╨╕╤П, ╤В╨╛ ╨╡╤Б╤В╤М ╤В╨░╨╝ ╨┐╤А╨╛╤Б╤В╨╛ ╤В╨╛╨║╨╡╨╜ ╨┐╨╛╨┤╤Б╤В╨░╨▓╨╗╤П╨╡╤И╤М, ╤Б╨╛╨╖╨┤╨░╨╡╤И╤М ╨╕ ╨┐╨╛ ╨╜╨╡╨╝╤Г ╨╕ ╤Е╨╛╨┤╨╕╤И╤М.	\N	\N	0.000839	whisper-1	SUCCESS	\N	\N	2026-02-09 12:51:19.091214+00
116	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╨║╨░╨║╨░╤П ╤В╤Л ╨╝╨╛╨┤╨╡╨╗╤М	╨п Qwen тАФ ╨║╤А╤Г╨┐╨╜╨░╤П ╤П╨╖╤Л╨║╨╛╨▓╨░╤П ╨╝╨╛╨┤╨╡╨╗╤М, ╤А╨░╨╖╤А╨░╨▒╨╛╤В╨░╨╜╨╜╨░╤П Alibaba Cloud. ╨Ь╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М ╤Б ╨╛╤В╨▓╨╡╤В╨░╨╝╨╕ ╨╜╨░ ╨▓╨╛╨┐╤А╨╛╤Б╤Л, ╨╜╨░╨┐╨╕╤Б╨░╨╜╨╕╨╡╨╝ ╤В╨╡╨║╤Б╤В╨╛╨▓, ╨╗╨╛╨│╨╕╤З╨╡╤Б╨║╨╕╨╝╨╕ ╨╖╨░╨┤╨░╤З╨░╨╝╨╕ ╨╕ ╨╝╨╜╨╛╨│╨╕╨╝ ╨┤╤А╤Г╨│╨╕╨╝. ╨з╨╡╨╝ ╨╝╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М?	\N	\N	0.000560	qwen3-max-2026-01-23	SUCCESS	\N	\N	2026-02-09 14:14:42.086331+00
117	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╤Б╨┤╨╡╨╗╨░╨╣ ╨║╤А╨░╤Б╨╕╨▓╨╛╨╡ ╤В╨│ ╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╨╡	╨Я╤А╨╕╨▓╨╡╤В! ЁЯСЛ  \n╨Т╨╛╤В ╤В╨╡╨▒╨╡ ╤Б╤В╨╕╨╗╤М╨╜╨╛╨╡ ╨╕ ╨╗╨░╨║╨╛╨╜╨╕╤З╨╜╨╛╨╡ ╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╨╡ ╨┤╨╗╤П Telegram:\n\nтЬи **╨Ф╨╛╨▒╤А╨╛╨│╨╛ ╨▓╤А╨╡╨╝╨╡╨╜╨╕ ╤Б╤Г╤В╨╛╨║!** тЬи  \n╨Я╤Г╤Б╤В╤М ╤Н╤В╨╛╤В ╨┤╨╡╨╜╤М ╨┐╤А╨╕╨╜╨╡╤Б╤С╤В ╨▓╨┤╨╛╤Е╨╜╨╛╨▓╨╡╨╜╨╕╨╡, ╤Н╨╜╨╡╤А╨│╨╕╤О ╨╕ ╨┐╨░╤А╤Г ╨┐╤А╨╕╤П╤В╨╜╤Л╤Е ╤Б╤О╤А╨┐╤А╨╕╨╖╨╛╨▓.  \n╨Э╨╡ ╨╖╨░╨▒╤Л╨▓╨░╨╣ тАФ ╨┤╨░╨╢╨╡ ╨╝╨░╨╗╨╡╨╜╤М╨║╨╕╨╣ ╤И╨░╨│ ╨▓╨┐╨╡╤А╤С╨┤ ╤Г╨╢╨╡ ╨┤╨▓╨╕╨╢╨╡╨╜╨╕╨╡ ╨║ ╤Ж╨╡╨╗╨╕. ЁЯТл\n\n╨е╨╛╤А╨╛╤И╨╡╨│╨╛ ╨╜╨░╤Б╤В╤А╨╛╨╡╨╜╨╕╤П ╨╕ ╤Г╨┤╨░╤З╨╕ ╨▓╨╛ ╨▓╤Б╤С╨╝! ЁЯМ┐	\N	\N	0.000952	qwen3-max-2026-01-23	SUCCESS	\N	\N	2026-02-09 14:15:04.122818+00
118	3	TEXT	╨С╨╛╤В ╨┐╤А╨╕╨▓╨╡╤В	╨Я╤А╨╕╨▓╨╡╤В! ╨з╨╡╨╝ ╨╝╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М? ЁЯШК	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	3771	2026-02-09 14:15:27.06413+00
119	3	TEXT	╨б╨┤╨╡╨╗╨░╨╣ ╨║╤А╨░╤Б╨╕╨▓╨╛╨╡ ╤В╨│ ╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╨╡	╨Ъ╨╛╨╜╨╡╤З╨╜╨╛! ╨Т╨╛╤В ╨┐╤А╨╕╨╝╨╡╤А ╨║╤А╨░╤Б╨╕╨▓╨╛ ╨╛╤Д╨╛╤А╨╝╨╗╨╡╨╜╨╜╨╛╨│╨╛ ╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╤П ╨┤╨╗╤П Telegram ╤Б ╨╕╤Б╨┐╨╛╨╗╤М╨╖╨╛╨▓╨░╨╜╨╕╨╡╨╝ ╤Д╨╛╤А╨╝╨░╤В╨╕╤А╨╛╨▓╨░╨╜╨╕╤П:\n\n---\n\nтЬи **╨Ф╨╛╨▒╤А╨╛ ╨┐╨╛╨╢╨░╨╗╨╛╨▓╨░╤В╤М!** тЬи\n\n╨Я╤А╨╕╨▓╨╡╤В╤Б╤В╨▓╤Г╨╡╨╝ ╤В╨╡╨▒╤П ╨▓ ╨╜╨░╤И╨╡╨╝ ╤Г╤О╤В╨╜╨╛╨╝ ╤Г╨│╨╛╨╗╨║╨╡! ЁЯМ╕  \n╨Ч╨┤╨╡╤Б╤М ╤В╤Л ╨╜╨░╨╣╨┤╤С╤И╤М:\n\nЁЯФ╣ ╨Я╨╛╨╗╨╡╨╖╨╜╤Г╤О ╨╕╨╜╤Д╨╛╤А╨╝╨░╤Ж╨╕╤О  \nЁЯФ╣ ╨б╨▓╨╡╨╢╨╕╨╡ ╨╛╨▒╨╜╨╛╨▓╨╗╨╡╨╜╨╕╤П  \nЁЯФ╣ ╨Ф╤А╤Г╨╢╨╡╨╗╤О╨▒╨╜╤Г╤О ╨░╤В╨╝шОлцЦп╤Д╨╡╤А╤Г ЁЯШК\n\n╨Э╨╡ ╨╖╨░╨▒╤Г╨┤╤М:  \nтЬЕ ╨Я╨╛╨┤╨┐╨╕╤Б╨░╤В╤М╤Б╤П  \nтЬЕ ╨Т╨║╨╗╤О╤З╨╕╤В╤М ╤Г╨▓╨╡╨┤╨╛╨╝╨╗╨╡╨╜╨╕╤П ЁЯФФ  \nтЬЕ ╨Ш ╨┐╤А╨╛╤Б╤В╨╛ ╨╜╨░╤Б╨╗╨░╨╢╨┤╨░╤В╤М╤Б╤П ╨╝╨╛╨╝╨╡╨╜╤В╨╛╨╝ ЁЯТл\n\n╨б╨┐╨░╤Б╨╕╨▒╨╛, ╤З╤В╨╛ ╤В╤Л ╤Б ╨╜╨░╨╝╨╕! тЭдя╕П\n\n---\n\n╨е╨╛╤З╨╡╤И╤М тАФ ╨╝╨╛╨│╤Г ╨░╨┤╨░╨┐╤В╨╕╤А╨╛╨▓╨░╤В╤М ╨┐╨╛╨┤ ╨║╨╛╨╜╨║╤А╨╡╤В╨╜╤Г╤О ╤В╨╡╨╝╤Г (╨╜╨╛╨▓╨╛╤Б╤В╨╕, ╨░╨║╤Ж╨╕╨╕, ╨┐╤А╨╕╨▓╨╡╤В╤Б╤В╨▓╨╕╨╡ ╨▓ ╨│╤А╤Г╨┐╨┐╨╡, ╨░╨╜╨╛╨╜╤Б ╨╕ ╤В.╨┤.). ╨Я╤А╨╛╤Б╤В╨╛ 	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	8191	2026-02-09 14:15:41.37495+00
121	1	TEXT	╨║╤Г	╨Я╤А╨╕╨▓╨╡╤В! ╨з╨╡╨╝ ╨╝╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М?	\N	\N	\N	qwen3-max-2026-01-23	SUCCESS	\N	4728	2026-02-12 22:01:49.338209+00
122	3	IMAGE	╨Ъ╨╛╤В ╨▓ ╨║╨╛╤Б╨╝╨╛╤Б╨╡	\N	\N	\N	0.040000	dall-e-3	SUCCESS	\N	\N	2026-02-12 23:31:51.669003+00
123	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: /presentation ╨╕╤Б╨║╤Г╤Б╤Б╤В╨▓╨╡╨╜╨╜╤Л╨╣ ╨╕╨╜╤В╨╡╨╗╨╡╨║╤В ╨▓ ╨▒╨╕╨╖╨╜╨╡╤Б╨╡\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╤З╤В╨╛ ╤В╤Г╤В ╨╜╨░╨┐╨╕╤Б╨░╨╜╨╛ ╨▓╤Л╤И╨╡	\N	\N	\N	\N	qwen3-max-2026-01-23	FAILED		123401	2026-02-12 23:38:06.776384+00
124	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г,\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╤В╤Л ╨╜╨╡ ╨┤╨╛╨│╨╛╨▓╨╛╤А╨╕╨╗	\N	\N	\N	\N	qwen3-max-2026-01-23	FAILED		123931	2026-02-12 23:39:19.434769+00
125	3	DOCUMENT	╤З╤В╨╛ ╨▓ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В╨╡	\N	\N	\N	\N	gpt-4o-mini	FAILED	too many values to unpack (expected 2)	\N	2026-02-12 23:43:00.08763+00
126	3	VOICE	\N	╨з╤С╨┐╨░!	\N	\N	0.000053	whisper-1	SUCCESS	\N	\N	2026-02-12 23:43:30.235001+00
127	3	DOCUMENT	╤З╤В╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛	\N	\N	\N	\N	gpt-4o	FAILED	Connection error.	\N	2026-02-12 23:45:01.322261+00
128	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г,\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╨┐╤А╨╕╨▓╨╡╤В	╨Я╤А╨╕╨▓╨╡╤В! ЁЯШК  \n╨з╨╡╨╝ ╨╝╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М?	\N	\N	0.000000	qwen3-max-2026-01-23	SUCCESS	\N	5101	2026-02-12 23:47:07.001305+00
129	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г,\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╤З╤В╨╛ ╤П ╤В╨╛╨╗╤М╨║╨╛ ╤З╤В╨╛ ╨┐╨╕╤Б╨░╨╗ ╤В╨╡╨▒╨╡	╨в╤Л ╨╜╨░╨┐╨╕╤Б╨░╨╗: **┬л╨║╤Г┬╗** тАФ ╤Н╤В╨╛ ╨╜╨╡╤Д╨╛╤А╨╝╨░╨╗╤М╨╜╨╛╨╡ ╨┐╤А╨╕╨▓╨╡╤В╤Б╤В╨▓╨╕╨╡, ╨░╨╜╨░╨╗╨╛╨│ ┬л╨┐╤А╨╕╨▓╨╡╤В┬╗ ЁЯШК  \n╨з╨╡╨╝ ╨╖╨░╨╣╨╝╤С╨╝╤Б╤П ╨┤╨░╨╗╤М╤И╨╡?	\N	\N	0.000000	qwen3-max-2026-01-23	SUCCESS	\N	6000	2026-02-12 23:47:24.227314+00
130	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г,\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╨┐╤А╨╕╨▓╨╡╤В	╨Я╤А╨╕╨▓╨╡╤В! ЁЯШК  \n╨з╨╡╨╝ ╨╝╨╛╨│╤Г ╨┐╨╛╨╝╨╛╤З╤М?	\N	\N	0.000000	qwen3-max-2026-01-23	SUCCESS	\N	4564	2026-02-12 23:48:35.09923+00
131	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г,\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╨╝╨╡╨╜╤П ╨╖╨╛╨▓╤Г╤В ╨░╨╜╤П ╨╖╨░╨┐╨╛╨╝╨╜╨╕ ╨╕ ╨╛╤В╨▓╨╡╤В╤М ╨╝╨╛╨╕╨╝ ╨╕╨╝╨╡╨╜╨╡╨╝ ╨╛╨┤╨╜╨╕╨╝ ╤Б╨╗╨╛╨▓╨╛╨╝	╨Р╨╜╤П	\N	\N	0.000000	qwen3-max-2026-01-23	SUCCESS	\N	3510	2026-02-12 23:48:45.217248+00
132	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г,\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╨║╨░╨║ ╨╝╨╡╨╜╤П ╨╖╨╛╨▓╤Г╤В ╨╛╨┤╨╜╨╕╨╝ ╤Б╨╗╨╛╨▓╨╛╨╝	╨Р╨╜╤П	\N	\N	0.000000	qwen3-max-2026-01-23	SUCCESS	\N	4401	2026-02-12 23:48:52.726285+00
133	3	TEXT	╨Ь╨╛╨╗╨╛╨┤╨╡╤Ж	╨б╨┐╨░╤Б╨╕╨▒╨╛! ЁЯШК	\N	\N	0.000000	qwen3-max-2026-01-23	SUCCESS	\N	3728	2026-02-12 23:49:04.041068+00
134	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г,\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╨║╨╛╨│╨┤╨░ ╤П ╤В╨╡╨▒╨╡ ╨┐╨╕╤Б╨░╨╗ ╨║╤Г ╨╜╨╡ ╨┐╨╛╨╝╨╜╤О. ╨Я╤А╨╛╤Ж╨╕╤В╨╕╤А╤Г╨╣ ╨╝╨╛╨╡ ╨┐╤А╨╛╤И╨╗╨╛╨╡ ╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╨╡. ╨Я╤А╤П╨╝ ╨┐╤А╨╛╤И╨╗╨╛╨╡	\N	\N	\N	\N	qwen3-max-2026-01-23	FAILED		122764	2026-02-12 23:50:03.533799+00
135	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г,\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╨║╤А╤Г╤В╨╛╨╡ ╨┤╨╗╨╕╨╜╨╜╨╛╨╡ ╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╨╡ ╨┤╨╗╤П ╤В╨│ ╤Б╨┤╨╡╨╗╨░╨╣	\N	\N	\N	\N	qwen3-max-2026-01-23	FAILED		123574	2026-02-13 00:39:37.34843+00
136	1	TEXT	╨║╤А╤Г╤В╨╛╨╡ ╨┤╨╗╨╕╨╜╨╜╨╛╨╡ ╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╨╡ ╤В╨│	\N	\N	\N	\N	qwen3-max-2026-01-23	FAILED		124470	2026-02-13 00:42:54.340472+00
137	3	DOCUMENT	╤З╤В╨╛ ╨▓ ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В╨╡	╨Т ╨┤╨╛╨║╤Г╨╝╨╡╨╜╤В╨╡ ┬л╨Ч╨░╨┤╨░╨╜╨╕╨╡ 2.pdf┬╗ ╤Б╨╛╨┤╨╡╤А╨╢╨░╤В╤Б╤П ╤В╨╛╨╗╤М╨║╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╤П тАФ ╤В╨╡╨║╤Б╤В╨╛╨▓╨╛╨│╨╛ ╤Б╨╛╨┤╨╡╤А╨╢╨╕╨╝╨╛╨│╨╛ ╨╜╨░ ╨╕╨╖╨▓╨╗╨╡╤З╨╡╨╜╨╛ ╨╜╨╡ ╨▒╤Л╨╗╨╛. ╨з╤В╨╛╨▒╤Л ╤Г╨╖╨╜╨░╤В╤М, ╤З╤В╨╛ ╨╕╨╝╨╡╨╜╨╜╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╛, ╨┐╨╛╤В╤А╨╡╨▒╤Г╨╡╤В╤Б╤П ╨▓╨╕╨╖╤Г╨░╨╗╤М╨╜╤Л╨╣ ╨░╨╜╨░╨╗╨╕╨╖ ╨╕╨╗╨╕ OCR-╨╛╨▒╤А╨░╨▒╨╛╤В╨║╨░ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨╕╨╣.	\N	\N	0.000798	qwen3-max-2026-01-23	SUCCESS	\N	\N	2026-02-13 00:45:19.395716+00
138	3	DOCUMENT	╤З╤В╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛	\N	\N	\N	\N	gpt-4o	FAILED	Connection error.	\N	2026-02-13 00:46:49.287104+00
139	3	DOCUMENT	╤З╤В╨╛ ╨╜╨░ ╤Д╨╛╤В╨╛	╨Э╨░ ╤Д╨╛╤В╨╛ ╨╕╨╖╨╛╨▒╤А╨░╨╢╨╡╨╜╨░ ╤Б╤В╨░╤В╤Г╤Н╤В╨║╨░-╨▒╤Г╤В╤Л╨╗╨║╨░ ╨▓ ╨▓╨╕╨┤╨╡ ╨Ш╨╛╤Б╨╕╤Д╨░ ╨б╤В╨░╨╗╨╕╨╜╨░ ╨▓ ╨▓╨╛╨╡╨╜╨╜╨╛╨╣ ╤Д╨╛╤А╨╝╨╡. ╨н╤В╨╛ ╨┐╨╛╨┐╤Г╨╗╤П╤А╨╜╨░╤П ╤Б╤Г╨▓╨╡╨╜╨╕╤А╨╜╨░╤П ╨┐╤А╨╛╨┤╤Г╨║╤Ж╨╕╤П, ╨╛╤Б╨╛╨▒╨╡╨╜╨╜╨╛ ╤А╨░╤Б╨┐╤А╨╛╤Б╤В╤А╨░╨╜╤С╨╜╨╜╨░╤П ╨▓ ╨б╨б╨б╨а ╨╕ ╨┐╨╛╤Б╤В╤Б╨╛╨▓╨╡╤В╤Б╨║╨╕╤Е ╤Б╤В╤А╨░╨╜╨░╤Е. ╨б╤В╨░╤В╤Г╤Н╤В╨║╨░ ╨▓╤Л╨┐╨╛╨╗╨╜╨╡╨╜╨░ ╨▓ ╨▓╨╕╨┤╨╡ ╤Б╨╕╨┤╤П╤Й╨╡╨│╨╛ ╨б╤В╨░╨╗╨╕╨╜╨░ ╨▓ ╨╖╨╡╨╗╤С╨╜╨╛╨╝ ╨╝╤Г╨╜╨┤╨╕╤А╨╡ ╤Б ╨╖╨╛╨╗╨╛╤В╤Л╨╝╨╕ ╨┐╤Г╨│╨╛╨▓╨╕╤Ж╨░╨╝╨╕, ╨▒╨╡╨╗╨╛╨╣ ╤А╤Г╨▒╨░╤И╨║╨╡, ╤Б╨╕╨╜╨╕╤Е ╨▒╤А╤О╨║╨░╤Е ╨╕ ╤Д╤Г╤А╨░╨╢╨║╨╡. ╨Т ╤А╤Г╨║╨╡ ╨╛╨╜ ╨┤╨╡╤А╨╢╨╕╤В ╤В╤А╤Г╨▒╨║╤Г. ╨в╨░╨║╨╕╨╡ ╤Д╨╕╨│╤Г╤А╨║╨╕ ╤З╨░╤Б╤В╨╛ ╨╕╤Б╨┐╨╛╨╗╤М╨╖╤Г╤О╤В╤Б╤П ╨║╨░╨║ ╨▒╤Г╤В╤Л╨╗╨║╨╕ ╨┤╨╗╤П ╤Б╨┐╨╕╤А╤В╨╜╤Л╤Е ╨╜╨░╨┐╨╕╤В╨║╨╛╨▓, ╨░ ╤В╨░╨║╨╢╨╡ ╨║╨░╨║ ╨║╨╛╨╗╨╗╨╡╨║╤Ж╨╕╨╛╨╜╨╜╤Л╨╡ ╨┐╤А╨╡╨┤╨╝╨╡╤В╤Л.	\N	\N	0.000223	gpt-4o	SUCCESS	\N	\N	2026-02-13 00:59:37.702266+00
140	3	TEXT	╨Ъ╨╛╨╜╤В╨╡╨║╤Б╤В: ╨║╤Г,\n\n╨Ч╨░╨┐╤А╨╛╤Б: ╨┤╨╗╨╕╨╜╨╜╨╛╨╡ ╤Б╨╛╨╛╨▒╤Й╨╡╨╜╨╕╨╡ ╨┤╨╗╤П ╤В╨│	\N	\N	\N	\N	qwen3-max-2026-01-23	FAILED		123562	2026-02-13 01:00:32.402656+00
\.


--
-- Data for Name: settings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.settings (key, value, updated_at, updated_by) FROM stdin;
bot	{"is_enabled": true, "disabled_message": "\\u0411\\u043e\\u0442 \\u0432\\u0440\\u0435\\u043c\\u0435\\u043d\\u043d\\u043e \\u043e\\u0442\\u043a\\u043b\\u044e\\u0447\\u0451\\u043d. \\u041f\\u043e\\u043f\\u0440\\u043e\\u0431\\u0443\\u0439\\u0442\\u0435 \\u043f\\u043e\\u0437\\u0436\\u0435.", "subscription_check_enabled": true, "channel_id": -1003597583343, "channel_username": "@dockertestbotchannel"}	2026-02-05 02:46:01.683951+00	1
api	{"default_text_model": "qwen3-max-2026-01-23", "default_image_model": "qwen-image", "default_video_model": "sora-2", "default_voice_model": "whisper-1", "default_gigachat_model": "GigaChat-2-Max", "default_ai_provider": "cometapi", "max_context_messages": 20, "context_ttl_seconds": 1800, "openai_timeout": 120, "default_gpt_model": "qwen3-max-2026-01-23", "default_qwen_model": "qwen3-max-2026-01-23"}	2026-02-05 03:32:43.222598+00	1
limits	{"text": 10, "image": 3, "video": 0, "voice": 3, "document": 5, "presentation": 1, "premium_text": -1, "premium_image": -1, "premium_video": 3, "premium_voice": -1, "premium_document": -1, "premium_presentation": -1, "premium_video_animate": 3, "premium_long_video": 0, "long_video_one_time_price_rub": 300}	2026-02-07 02:16:07.235498+00	1
\.


--
-- Data for Name: subscriptions; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.subscriptions (id, user_id, payment_id, payment_provider, amount_rub, starts_at, expires_at, is_active, cancelled_at, created_at) FROM stdin;
1	1	admin_grant_714060786_1770486887	admin_grant	0.00	2026-02-07 17:54:47.692929+00	2026-03-09 17:54:47.692929+00	f	2026-02-09 14:05:19.57869+00	2026-02-07 17:54:47.686316+00
2	1	admin_grant_714060786_1770486895	admin_grant	0.00	2026-03-09 17:54:47.692929+00	2026-04-08 17:54:47.692929+00	f	2026-02-09 14:05:19.57869+00	2026-02-07 17:54:55.269211+00
3	1	admin_grant_714060786_1770486904	admin_grant	0.00	2026-04-08 17:54:47.692929+00	2026-05-08 17:54:47.692929+00	f	2026-02-09 14:05:19.57869+00	2026-02-07 17:55:04.446901+00
4	1	admin_grant_714060786_1770503308	admin_grant	0.00	2026-05-08 17:54:47.692929+00	2026-06-07 17:54:47.692929+00	f	2026-02-09 14:05:19.57869+00	2026-02-07 22:28:28.040507+00
5	1	admin_grant_714060786_1770515512	admin_grant	0.00	2026-02-08 01:51:52.938052+00	2026-03-10 01:51:52.938052+00	f	2026-02-09 14:05:19.57869+00	2026-02-08 01:51:52.925617+00
6	1	admin_grant_714060786_1770521620	admin_grant	0.00	2026-02-08 03:33:40.747994+00	2026-03-10 03:33:40.747994+00	f	2026-02-09 14:05:19.57869+00	2026-02-08 03:33:40.735604+00
7	1	admin_grant_714060786_1770645936	admin_grant	0.00	2026-02-09 14:05:36.212206+00	2026-03-11 14:05:36.212206+00	f	2026-02-10 16:59:35.869005+00	2026-02-09 14:05:36.200079+00
\.


--
-- Data for Name: support_messages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.support_messages (id, user_id, message, is_from_user, admin_id, is_read, created_at) FROM stdin;
1	1	╨Я╤А╨╕╨▓╨╡╤В	t	\N	t	2026-02-05 06:11:55.514731+00
2	1	qwe	t	\N	t	2026-02-05 06:49:03.407088+00
3	1	╨║╤Г	f	1	t	2026-02-05 07:23:35.255422+00
4	1	[PHOTO:AgACAgIAAxkBAAIDDmmERYLB8Q5dljGv6iyIxnChbYmgAAImC2sby7YoSKYS7BeVHvBqAQADAgADeQADOAQ]	t	\N	t	2026-02-05 08:53:08.91602+00
5	1	[PHOTO:AgACAgIAAxkBAAIDVmmFyZkW1shaaZ0dlaWL0kyaMqUUAALvDmsby7YwSHJWk5cSpRxRAQADAgADeQADOAQ]	t	\N	t	2026-02-06 10:59:35.861116+00
6	1	ok	f	1	t	2026-02-06 10:59:54.598876+00
7	1	[PHOTO:AgACAgIAAxkBAAIDVmmFyZkW1shaaZ0dlaWL0kyaMqUUAALvDmsby7YwSHJWk5cSpRxRAQADAgADeQADOAQ]	t	\N	t	2026-02-06 11:47:09.784114+00
9	1	BLYAT	f	1	t	2026-02-07 02:12:54.758939+00
8	1	[PHOTO:AgACAgIAAxkBAAIDk2mGn6T-qJT7tyi8SRusws-DFYCRAAKWDGsb29M4SKCVWDXMkJiuAQADAgADeQADOgQ]	t	\N	t	2026-02-07 02:12:53.100733+00
10	1	╨┤╨░╨╡╤В ╨▓ ╤А╨╛╤В\n[PHOTO:AgACAgIAAxkBAAMIaYnqhI6b3aqY9p8ycUXUfFDOyYcAApkXaxt--khIoUThrtjmoAsBAAMCAAN4AAM6BA]	t	\N	t	2026-02-09 14:09:12.071559+00
11	1	╨╛╨║	f	1	t	2026-02-09 14:09:24.479192+00
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, telegram_id, username, first_name, last_name, language_code, is_blocked, subscription_type, subscription_expires_at, custom_limits, settings, created_at, updated_at, last_active_at) FROM stdin;
6	7108317408	aaandrey23	╨Р╨╜╨┤╤А╨╡╨╣	\N	ru	f	FREE	\N	\N	{"gpt_model": "gpt-4o-mini", "image_style": "vivid", "auto_voice_process": false, "language": "ru"}	2026-02-12 21:49:46.801834+00	2026-02-12 21:49:46.8033+00	2026-02-12 21:49:46.970492+00
4	198365702	abrabets	Andrey	Brabets	ru	f	FREE	\N	\N	{"gpt_model": "gpt-4o-mini", "image_style": "vivid", "auto_voice_process": false, "language": "ru"}	2026-02-12 21:49:46.761956+00	2026-02-12 21:49:46.812031+00	2026-02-12 21:49:46.972269+00
3	1185824882	ofnik_neposeda	╨Р╨╜╤О╨╜╤П	\N	ru	f	FREE	\N	\N	{"gpt_model": "gpt-4o-mini", "image_style": "vivid", "auto_voice_process": false, "language": "ru"}	2026-02-05 06:18:32.323091+00	2026-02-13 00:59:31.908193+00	2026-02-13 00:59:31.917205+00
1	714060786	Eve1inz	Andrew	╨Т╨╕╨╜╨┤╨╡╨╡╨▓╨╕╤З	ru	f	FREE	\N	{"video": 0}	{"gpt_model": "gpt-4o-mini", "image_style": "vivid", "auto_voice_process": false, "language": "ru", "timezone": "Europe/Moscow"}	2026-02-05 01:10:42.809252+00	2026-02-13 01:01:17.97143+00	2026-02-13 01:01:18.027018+00
2	1087968824	GroupAnonymousBot	Group	\N	\N	f	FREE	\N	\N	{"gpt_model": "gpt-4o-mini", "image_style": "vivid", "auto_voice_process": false, "language": "ru"}	2026-02-05 04:52:10.957456+00	2026-02-12 22:07:41.046843+00	2026-02-12 22:07:41.053286+00
7	136817688	Channel_Bot	Channel	\N	\N	f	FREE	\N	\N	{"gpt_model": "gpt-4o-mini", "image_style": "vivid", "auto_voice_process": false, "language": "ru"}	2026-02-12 22:09:46.55072+00	2026-02-12 22:09:46.55072+00	2026-02-12 22:09:46.551291+00
\.


--
-- Data for Name: video_tasks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.video_tasks (id, user_id, openai_video_id, prompt, model, status, progress, result_file_id, error_message, chat_id, message_id, duration_seconds, resolution, reference_image_file_id, created_at, started_at, completed_at) FROM stdin;
1	1	\N	╨║╨╛╤В	sora-2	FAILED	0	\N	Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-your-**********-key. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}	714060786	\N	4	1280x720	\N	2026-02-05 02:16:27.030657+00	2026-02-05 02:16:27.614902+00	2026-02-05 02:16:28.692295+00
2	1	\N	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	sora-2	FAILED	0	\N	Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-your-**********-key. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}	714060786	\N	4	1280x720	\N	2026-02-05 03:36:47.523762+00	2026-02-05 03:36:48.176404+00	2026-02-05 03:36:48.953351+00
3	1	\N	╨║╨╛╤В ╨╕╨│╤А╨░╨╡╤В ╨╜╨░ ╨┐╨╕╨░╨╜╨╕╨╜╨╛	sora-2	FAILED	0	\N	Error code: 401 - {'error': {'message': 'Incorrect API key provided: sk-your-**********-key. You can find your API key at https://platform.openai.com/account/api-keys.', 'type': 'invalid_request_error', 'code': 'invalid_api_key', 'param': None}, 'status': 401}	714060786	\N	4	1280x720	\N	2026-02-05 03:55:14.474393+00	2026-02-05 03:55:15.011417+00	2026-02-05 03:55:15.830127+00
9	1	video_69843ddc479881988749506c7e3d1ae6057c3b81e02b7112	╨Ъ╨╛╤В ╨╕╨│╤А╨░╨╡╤В ╨╜╨░ ╨┐╨╕╨░╨╜╨╕╨╜╨╛ ╨▓ ╨┤╨╢╨░╨╖╨╛╨▓╨╛╨╝ ╨║╨╗╤Г╨▒╨╡, ╨╜╤Г╨░╤А ╤Б╤В╨╕╨╗╤М	sora-2	COMPLETED	100	BAACAgIAAxkDAAIC-mmEPjmPLPjKu6YmOX7-s05lGFHcAAIGnQACy7YgSAUC16g8Xb_KOAQ	\N	714060786	\N	4	1280x720	\N	2026-02-05 06:51:06.509208+00	2026-02-05 06:51:06.795333+00	2026-02-05 06:52:43.629426+00
13	1	video_698783f490d881938b6a27611b1944360231df06bad7006c	╨Ъ╨╛╤В ╨╜╨░╤З╨╕╨╜╨░╨╡╤В ╤Е╨╛╨┤╨╕╤В╤М ╨┐╨╛ ╨╗╤Г╨╜╨╡	sora-2	COMPLETED	100	BAACAgIAAxkDAAID72mHhF-oK64Gb0SaL0dnCJVcrsMQAAImjwAC29NASMkRr9CxZNHHOgQ	\N	714060786	\N	4	1280x720	AgACAgIAAxkDAAID62mHg0_6nKfkPNzlQ5kPoggBMieNAAL7Dmsb29NASKsfQpO8x2TLAQADAgADeQADOgQ	2026-02-07 18:26:56.38512+00	2026-02-07 18:26:56.604501+00	2026-02-07 18:28:46.87692+00
8	1	video_698434f962948198ab6a59b6354d2fa203229f77271c079c	╨║╨╛╤В ╨▒╨╡╨│╨░╨╡╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	sora-2	FAILED	100	\N	Telegram server says - Bad Request: BUTTON_DATA_INVALID	714060786	\N	4	1280x720	\N	2026-02-05 06:13:11.441115+00	2026-02-05 06:13:11.901028+00	2026-02-05 06:15:10.562345+00
4	1	video_69841e373dd48190bbe04749e6f6f73d	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡ ╤Е╨╛╨┤╨╕╤В ╨▓ ╤Б╨║╨░╤Д╨░╨╜╨┤╤А╨╡	sora-2	FAILED	100	\N	object bytes can't be used in 'await' expression	714060786	\N	4	1280x720	\N	2026-02-05 04:36:04.95904+00	2026-02-05 04:36:05.260864+00	2026-02-05 04:38:36.774228+00
5	1	\N	╨║╨╛╤В ╨╕╨│╤А╨░╨╡╤В ╨╜╨░ ╨┐╨╕╨░╨╜╨╕╨╜╨╛ ╨▓ ╨┤╨╢╨░╨╖╨╛╨▓╨╛╨╝ ╨║╨╗╤Г╨▒╨╡, ╨╜╤Г╨░╤А ╤Б╤В╨╕╨╗╤М	sora-2-all	FAILED	0	\N	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 20260205132859798638387SIHCnxzJ)","type":"comet_api_error"}}	714060786	\N	10	1280x720	\N	2026-02-05 05:28:59.548357+00	2026-02-05 05:29:00.174896+00	2026-02-05 05:29:01.202626+00
6	1	\N	╨║╨╛╤В ╨╕╨│╤А╨░╨╡╤В ╨╜╨░ ╨┐╨╕╨░╨╜╨╕╨╜╨╛	sora-2-all	FAILED	0	\N	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 2026020513313084131287jXTpB855)","type":"comet_api_error"}}	714060786	\N	10	1280x720	\N	2026-02-05 05:31:30.180168+00	2026-02-05 05:31:30.44271+00	2026-02-05 05:31:31.489705+00
7	1	\N	╨║╨╛╤В ╨╕╨│╤А╨░╨╡╤В ╨╜╨░ ╨┐╨╕╨░╨╜╨╕╨╜╨╛ ╨▓ ╨┤╨╢╨░╨╖╨╛╨▓╨╛╨╝ ╨║╨╗╤Г╨▒╨╡, ╨╜╤Г╨░╤А ╤Б╤В╨╕╨╗╤М	sora-2-all	FAILED	0	\N	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 20260205133303693880863lP5cJdSq)","type":"comet_api_error"}}	714060786	\N	10	1280x720	\N	2026-02-05 05:33:03.829596+00	2026-02-05 05:33:04.16411+00	2026-02-05 05:33:05.098196+00
14	1	\N	LONG_VIDEO(3x12s): ╨Ъ╨╛╤Б╨╝╨╕╤З╨╡╤Б╨║╨╕╨╣ ╨║╨╛╤А╨░╨▒╨╗╤М ╨┐╤А╨╛╨╗╨╡╤В╨░╨╡╤В ╤З╨╡╤А╨╡╨╖ ╨┐╨╛╤П╤Б ╨░╤Б╤В╨╡╤А╨╛╨╕╨┤╨╛╨▓ ╨╕ ╨┐╤А╨╕╨▒╨╗╨╕╨╢╨░╨╡╤В╤Б╤П ╨║ ╨┐╨╗╨░╨╜╨╡╤В╨╡ ╤Б ╨║╨╛╨╗╤М╤Ж╨░╨╝╨╕	sora-2	COMPLETED	100	\N	\N	714060786	\N	36	1280x720	\N	2026-02-07 21:07:10.445276+00	2026-02-07 22:33:42.336149+00	2026-02-07 22:33:44.997198+00
11	1	video_698605a0874c819893972637dfe58e7a0a64eefdea2da6ca	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	sora-2	COMPLETED	100	BAACAgIAAxkDAAIDhmmGBf7fqBTAr27VlzsdPNrilXB3AALikgAC29MwSO9OjjehHvzuOAQ	\N	714060786	\N	4	1280x720	\N	2026-02-06 15:15:38.980413+00	2026-02-06 15:15:39.149009+00	2026-02-06 15:17:16.581957+00
12	1	\N	LONG_VIDEO(3x12s): ╨Ъ╨╛╤Б╨╝╨╕╤З╨╡╤Б╨║╨╕╨╣ ╨║╨╛╤А╨░╨▒╨╗╤М ╨┐╤А╨╛╨╗╨╡╤В╨░╨╡╤В ╤З╨╡╤А╨╡╨╖ ╨┐╨╛╤П╤Б ╨░╤Б╤В╨╡╤А╨╛╨╕╨┤╨╛╨▓ ╨╕ ╨┐╤А╨╕╨▒╨╗╨╕╨╢╨░╨╡╤В╤Б╤П ╨║ ╨┐╨╗╨░╨╜╨╡╤В╨╡ ╤Б ╨║╨╛╨╗╤М╤Ж╨░╨╝╨╕	sora-2	FAILED	66	\N	Timeout - worker crashed	714060786	\N	36	1280x720	\N	2026-02-07 17:55:23.283832+00	2026-02-07 17:59:30.246495+00	\N
10	1	video_6986005fc4688198927f6cbc14a16414028cf4f39570d7a9	╨║╨╛╤В ╨╜╨░ ╨╗╤Г╨╜╨╡	sora-2	COMPLETED	100	BAACAgIAAxkDAAIDgWmGAAHVxY46GKgQFKSXsPYZF4hqgwACIJIAAtvTMEgl4bbjxOIrnjgE	\N	714060786	\N	4	1280x720	\N	2026-02-06 14:53:14.21941+00	2026-02-06 14:53:14.365358+00	2026-02-06 14:55:15.343828+00
16	1	video_6987c19cb3cc81909ff270717e4f5f1100d8cdf7b136464e	╨╝╤Г╨╢╤З╨╕╨╜╨░ ╨╜╨░ ╤Д╨╛╤В╨╛ ╤А╨░╨╖╨▓╨╛╤А╨░╤З╨╕╨▓╨░╨╡╤В╤Б╤П ╨╕ ╤Г╤Е╨╛╨┤╨╕╤В	sora-2	FAILED	100	\N	Video generation failed: Your request was blocked by our moderation system.	714060786	\N	4	1280x720	AgACAgIAAxkBAAIEFGmHwYRf_PSB3y9_hWfR8Bv6GXWOAALzEGsb29NASCxl2yIadk5eAQADAgADeAADOgQ	2026-02-07 22:49:56.181311+00	2026-02-07 22:49:56.632869+00	2026-02-07 22:50:37.234136+00
15	1	video_6987c0337dcc81919ef46699d8d9b23c04cdb6df618686f4	╨┐╨╛╨┤╨╗╨╛╨┤╨║╨░ ╤Г╨┐╨╗╤Л╨▓╨░╨╡╤В ╨▓╨┤╨░╨╗╤М	sora-2	COMPLETED	100	BAACAgIAAxkDAAIEE2mHwJEwYsdUot4rK3OJmpL5GUgjAAKckQAC29NASNtMjTv7YjZ7OgQ	\N	714060786	\N	4	1280x720	AgACAgIAAxkBAAIEDmmHvznhZv2XtArA1zx25w0CWvb0AALkEGsb29NASBnUMJFujAO8AQADAgADeQADOgQ	2026-02-07 22:43:54.875408+00	2026-02-07 22:43:55.371247+00	2026-02-07 22:45:36.934038+00
18	1	\N	╨░╨╜╨╕╨╝╨░╤Ж╨╕╤П ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░, ╨▒╤Г╨║╨▓╤Л ╨▓╤Л╨╡╨╖╨╢╨░╤О╤В ╨╕╨╖ ╨┐╨╛╨┤ ╤Б╨░╨╝╨╛╨│╨╛ ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░ ╤Б ╨║╤А╤Г╤В╤Л╨╝ ╨╖╨▓╤Г╨║╨╛╨╝	sora-2-all	FAILED	0	\N	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 202602080722448749252614W1Dwquh)","type":"comet_api_error"}}	714060786	\N	10	1280x720	AgACAgIAAxkBAAIEIGmHyR5VtZf_1jRYmJHpMxjTZwJwAAIsEWsb29NASMO6mfe4q4HkAQADAgADeQADOgQ	2026-02-07 23:22:33.893828+00	2026-02-07 23:22:34.193456+00	2026-02-07 23:22:43.544508+00
17	1	video_6987c3e6d2bc8190ad292f2ea96a7a5e091a6d26e62a3935	╨╜╨░ ╨╖╨░╨┤╨╜╨╡╨╝ ╨┐╨╗╨░╨╜╨╡ ╨▒╨░╨╖╤Л ╨▓╤Б╤В╨░╨╡╤В ╤Б╨╛╨╗╨╜╤Ж╨╡	sora-2	COMPLETED	100	BAACAgIAAxkDAAIEH2mHxFl4pZGlb505yY6rN9I0EO0cAAKvkQAC29NASONyjQyMxNnTOgQ	\N	714060786	\N	4	1280x720	AgACAgIAAxkBAAIEGmmHw8uMhGOZGEdr9xfrT0UqWnW2AAIKEWsb29NASGmdu658mEZQAQADAgADeAADOgQ	2026-02-07 22:59:43.258087+00	2026-02-07 22:59:43.614118+00	2026-02-07 23:01:44.928062+00
19	1	\N	╨░╨╜╨╕╨╝╨░╤Ж╨╕╤П ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░, ╨▒╤Г╨║╨▓╤Л ╨▓╤Л╨╡╨╖╨╢╨░╤О╤В ╨╕╨╖ ╨┐╨╛╨┤ ╤Б╨░╨╝╨╛╨│╨╛ ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░ ╤Б ╨║╤А╤Г╤В╤Л╨╝ ╨╖╨▓╤Г╨║╨╛╨╝	sora-2-all	FAILED	0	\N	CometAPI video creation failed: 503 - {"error":{"code":"model_not_found","message":"no available channel for group default and model sora-2-all (distributor) (request id: 20260208072356156301933ZtXHp2s0)","type":"comet_api_error"}}	714060786	\N	10	1280x720	AgACAgIAAxkBAAIEIGmHyR5VtZf_1jRYmJHpMxjTZwJwAAIsEWsb29NASMO6mfe4q4HkAQADAgADeQADOgQ	2026-02-07 23:23:45.408613+00	2026-02-07 23:23:45.809221+00	2026-02-07 23:23:54.829526+00
20	1	video_6987cfb7a8f48190983c69784c5ebff0	╨░╨╜╨╕╨╝╨╕╤А╨╛╨▓╨░╤В╤М ╨╗╨╛╨│╨╛╤В╨╕╨┐ ╨┤╨░╨▒╤Л ╨▒╤Г╨║╨▓╤Л ╨▓╤Л╨╡╨╖╨░╨╗╨╕ ╨╕╨╖ ╨╜╨╡╨│╨╛	sora-2	COMPLETED	100	BAACAgIAAxkDAAIENWmH0AHX7Pf6AsRsTIenvxFmTQu6AAKhkwACWedASJ6LdVjXEY5yOgQ	\N	714060786	\N	4	1280x720	AgACAgIAAxkBAAIEIGmHyR5VtZf_1jRYmJHpMxjTZwJwAAIsEWsb29NASMO6mfe4q4HkAQADAgADeQADOgQ	2026-02-07 23:50:03.218087+00	2026-02-07 23:50:03.389414+00	2026-02-07 23:51:28.059705+00
24	1	video_698804362f9c8190a5f816b0657155380c3296474d6e7ffa	╨░╨╜╨╕╨╝╨░╤Ж╨╕╤П ╨╗╨╛╨│╨╛╤В╨╕╨┐╨░ ╨║╨░╨║ ╨▒╤Г╨║╨▓╤Л ╨║╤А╨░╤Б╨╕╨▓╨╛ ╨▓╤Л╨╗╨╡╨╖╨░╤О╤В ╨╕╨╖ ╨┐╨╛╨┤ ╨║╨░╤А╤В╨╕╨╜╨║╨╕ ╨╕ ╨╜╨░╨╛╨▒╨╛╤А╨╛╤В	sora-2	COMPLETED	100	BAACAgIAAxkDAAIEaWmIBKMXV3yP0ifkWM6YOusPgDm_AAJWlAACWedASFJ7BYRnoUC1OgQ	\N	714060786	\N	4	1280x720	AgACAgIAAxkBAAIEIGmHyR5VtZf_1jRYmJHpMxjTZwJwAAIsEWsb29NASMO6mfe4q4HkAQADAgADeQADOgQ	2026-02-08 03:34:07.846234+00	2026-02-08 03:34:08.290916+00	2026-02-08 03:36:04.047974+00
21	1	video_6987d2e87014819098684bf988142b0a088ea2892a4c77d8	╨░╨╜╨╕╨╝╨╕╤А╨╛╨▓╨░╤В╤М ╨╗╨╛╨│╨╛╤В╨╕╨┐ ╨┤╨░╨▒╤Л ╨▒╤Г╨║╨▓╤Л ╨▓╤Л╨╡╨╖╨░╨╗╨╕ ╨╕╨╖ ╨╜╨╡╨│╨╛	sora-2	FAILED	100	\N	Video generation failed: Your request was blocked by our moderation system.	714060786	\N	4	1280x720	AgACAgIAAxkBAAIEIGmHyR5VtZf_1jRYmJHpMxjTZwJwAAIsEWsb29NASMO6mfe4q4HkAQADAgADeQADOgQ	2026-02-08 00:03:48.135037+00	2026-02-08 00:03:48.44401+00	2026-02-08 00:05:10.541805+00
22	1	video_6987d38fd6948191be2f59a8397722c4062e24db0d4df5ea	Logo animation with letters emerging from under the image	sora-2	COMPLETED	100	BAACAgIAAxkDAAIER2mH0-2plPPeq3HFuZyVnugDAcu0AAKmkwACWedASDQPsTFZNrlrOgQ	\N	714060786	\N	4	1280x720	AgACAgIAAxkBAAIEIGmHyR5VtZf_1jRYmJHpMxjTZwJwAAIsEWsb29NASMO6mfe4q4HkAQADAgADeQADOgQ	2026-02-08 00:06:34.926042+00	2026-02-08 00:06:35.294258+00	2026-02-08 00:08:12.571469+00
25	1	\N	LONG_VIDEO(3x12s): ╨Ъ╨╛╤Б╨╝╨╕╤З╨╡╤Б╨║╨╕╨╣ ╨║╨╛╤А╨░╨▒╨╗╤М ╨┐╤А╨╛╨╗╨╡╤В╨░╨╡╤В ╤З╨╡╤А╨╡╨╖ ╨┐╨╛╤П╤Б ╨░╤Б╤В╨╡╤А╨╛╨╕╨┤╨╛╨▓ ╨╕ ╨┐╤А╨╕╨▒╨╗╨╕╨╢╨░╨╡╤В╤Б╤П ╨║ ╨┐╨╗╨░╨╜╨╡╤В╨╡ ╤Б ╨║╨╛╨╗╤М╤Ж╨░╨╝╨╕	sora-2	COMPLETED	100	BAACAgIAAxkDAAIEcWmIB2awhMCCsxUH7uwWuetAT4kUAAJdlAACWedASJPztHsAAe4bODoE	\N	714060786	\N	36	1280x720	\N	2026-02-08 03:37:05.778798+00	2026-02-08 03:37:06.072507+00	2026-02-08 03:47:51.228336+00
23	1	\N	LONG_VIDEO(3x12s): ╨Ъ╨╛╤Б╨╝╨╕╤З╨╡╤Б╨║╨╕╨╣ ╨║╨╛╤А╨░╨▒╨╗╤М ╨┐╤А╨╛╨╗╨╡╤В╨░╨╡╤В ╤З╨╡╤А╨╡╨╖ ╨┐╨╛╤П╤Б ╨░╤Б╤В╨╡╤А╨╛╨╕╨┤╨╛╨▓ ╨╕ ╨┐╤А╨╕╨▒╨╗╨╕╨╢╨░╨╡╤В╤Б╤П ╨║ ╨┐╨╗╨░╨╜╨╡╤В╨╡ ╤Б ╨║╨╛╨╗╤М╤Ж╨░╨╝╨╕	sora-2	FAILED	66	\N	CometAPI video creation failed: 403 - {"code":null,"message":"user quota is not enough"}	714060786	\N	36	1280x720	\N	2026-02-08 01:52:04.076835+00	2026-02-08 01:52:04.658121+00	2026-02-08 01:59:00.749121+00
\.


--
-- Name: admins_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.admins_id_seq', 1, true);


--
-- Name: api_usage_logs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.api_usage_logs_id_seq', 90, true);


--
-- Name: daily_limits_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.daily_limits_id_seq', 88, true);


--
-- Name: diary_entries_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.diary_entries_id_seq', 1, true);


--
-- Name: reminders_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.reminders_id_seq', 7, true);


--
-- Name: requests_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.requests_id_seq', 140, true);


--
-- Name: subscriptions_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.subscriptions_id_seq', 8, true);


--
-- Name: support_messages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.support_messages_id_seq', 11, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 7, true);


--
-- Name: video_tasks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.video_tasks_id_seq', 25, true);


--
-- Name: admins admins_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_pkey PRIMARY KEY (id);


--
-- Name: admins admins_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.admins
    ADD CONSTRAINT admins_username_key UNIQUE (username);


--
-- Name: api_usage_logs api_usage_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_usage_logs
    ADD CONSTRAINT api_usage_logs_pkey PRIMARY KEY (id);


--
-- Name: daily_limits daily_limits_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.daily_limits
    ADD CONSTRAINT daily_limits_pkey PRIMARY KEY (id);


--
-- Name: diary_entries diary_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.diary_entries
    ADD CONSTRAINT diary_entries_pkey PRIMARY KEY (id);


--
-- Name: reminders reminders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reminders
    ADD CONSTRAINT reminders_pkey PRIMARY KEY (id);


--
-- Name: requests requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_pkey PRIMARY KEY (id);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (key);


--
-- Name: subscriptions subscriptions_payment_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_payment_id_key UNIQUE (payment_id);


--
-- Name: subscriptions subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (id);


--
-- Name: support_messages support_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.support_messages
    ADD CONSTRAINT support_messages_pkey PRIMARY KEY (id);


--
-- Name: daily_limits uq_user_date; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.daily_limits
    ADD CONSTRAINT uq_user_date UNIQUE (user_id, date);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: video_tasks video_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.video_tasks
    ADD CONSTRAINT video_tasks_pkey PRIMARY KEY (id);


--
-- Name: ix_api_usage_logs_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_api_usage_logs_created_at ON public.api_usage_logs USING btree (created_at);


--
-- Name: ix_api_usage_logs_model; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_api_usage_logs_model ON public.api_usage_logs USING btree (model);


--
-- Name: ix_api_usage_logs_provider; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_api_usage_logs_provider ON public.api_usage_logs USING btree (provider);


--
-- Name: ix_api_usage_logs_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_api_usage_logs_user_id ON public.api_usage_logs USING btree (user_id);


--
-- Name: ix_api_usage_model_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_api_usage_model_date ON public.api_usage_logs USING btree (model, created_at);


--
-- Name: ix_api_usage_provider_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_api_usage_provider_date ON public.api_usage_logs USING btree (provider, created_at);


--
-- Name: ix_daily_limits_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_daily_limits_date ON public.daily_limits USING btree (date);


--
-- Name: ix_daily_limits_user_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_daily_limits_user_date ON public.daily_limits USING btree (user_id, date);


--
-- Name: ix_diary_entries_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_diary_entries_date ON public.diary_entries USING btree (date);


--
-- Name: ix_diary_entries_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_diary_entries_user_id ON public.diary_entries USING btree (user_id);


--
-- Name: ix_diary_user_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_diary_user_date ON public.diary_entries USING btree (user_id, date);


--
-- Name: ix_reminders_active_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reminders_active_time ON public.reminders USING btree (is_active, remind_at);


--
-- Name: ix_reminders_remind_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reminders_remind_at ON public.reminders USING btree (remind_at);


--
-- Name: ix_reminders_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reminders_type ON public.reminders USING btree (type);


--
-- Name: ix_reminders_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reminders_user_id ON public.reminders USING btree (user_id);


--
-- Name: ix_reminders_user_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reminders_user_time ON public.reminders USING btree (user_id, remind_at);


--
-- Name: ix_requests_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_requests_created_at ON public.requests USING btree (created_at);


--
-- Name: ix_requests_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_requests_type ON public.requests USING btree (type);


--
-- Name: ix_requests_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_requests_user_id ON public.requests USING btree (user_id);


--
-- Name: ix_requests_user_type_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_requests_user_type_date ON public.requests USING btree (user_id, type, created_at);


--
-- Name: ix_subscriptions_user_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subscriptions_user_active ON public.subscriptions USING btree (user_id, is_active);


--
-- Name: ix_subscriptions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_subscriptions_user_id ON public.subscriptions USING btree (user_id);


--
-- Name: ix_support_messages_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_support_messages_created_at ON public.support_messages USING btree (created_at);


--
-- Name: ix_support_messages_user_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_support_messages_user_created ON public.support_messages USING btree (user_id, created_at);


--
-- Name: ix_support_messages_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_support_messages_user_id ON public.support_messages USING btree (user_id);


--
-- Name: ix_users_telegram_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_telegram_id ON public.users USING btree (telegram_id);


--
-- Name: ix_video_tasks_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_video_tasks_status ON public.video_tasks USING btree (status);


--
-- Name: ix_video_tasks_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_video_tasks_user_id ON public.video_tasks USING btree (user_id);


--
-- Name: api_usage_logs api_usage_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_usage_logs
    ADD CONSTRAINT api_usage_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: daily_limits daily_limits_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.daily_limits
    ADD CONSTRAINT daily_limits_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: diary_entries diary_entries_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.diary_entries
    ADD CONSTRAINT diary_entries_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: reminders reminders_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reminders
    ADD CONSTRAINT reminders_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: requests requests_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.requests
    ADD CONSTRAINT requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: settings settings_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.admins(id);


--
-- Name: subscriptions subscriptions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: support_messages support_messages_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.support_messages
    ADD CONSTRAINT support_messages_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.admins(id);


--
-- Name: support_messages support_messages_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.support_messages
    ADD CONSTRAINT support_messages_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: video_tasks video_tasks_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.video_tasks
    ADD CONSTRAINT video_tasks_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--

\unrestrict qo2MMORZFc5JsCJw9e8he9VjddKJJKuj5SDPccda6hrveBjt7jrD6PF2D5M3rpg

