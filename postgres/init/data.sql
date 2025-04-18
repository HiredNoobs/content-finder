--
-- PostgreSQL database dump
--

-- Dumped from database version 9.6.10
-- Dumped by pg_dump version 9.6.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: content; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.content (
    channelid character varying(24) DEFAULT NULL::character varying PRIMARY KEY,
    name character varying(50) DEFAULT NULL::character varying,
    datetime character varying(25) DEFAULT NULL::character varying,
    tags text[]
);


ALTER TABLE public.content OWNER TO root;
