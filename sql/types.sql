--
-- Database types.
--
SET search_path TO kbpo;

CREATE TYPE SPAN AS (
  doc_id TEXT NOT NULL,
  char_begin INTEGER NOT NULL,
  char_end INTEGER NULL
);
COMMENT ON TYPE SPAN IS 'A span stores doc_id, doc_begin and doc_end.';

CREATE TYPE SCORE AS (
  precision REAL,
  recall REAL,
  f1 REAL
);
COMMENT ON TYPE SCORE IS 'The score contains precision, recall, f1.';

-- FIXME: These types are not supported by postgres 8.2 that is used by
-- Greenplum.
-- CREATE TYPE SCORE_TYPE AS ENUM (
--     'entity_macro',
--     'entity_micro',
--     'relation_macro',
--     'relation_micro',
--     'instance_macro',
--     'instance_micro'
-- );
-- COMMENT ON TYPE SCORE_TYPE IS 'The precise mode in which scores have been generated.';
-- 
-- CREATE TYPE EVALUATION_TYPE AS ENUM (
--     'exhaustive_document',
--     'exhaustive_relations',
--     'selective_relations'
-- );
-- COMMENT ON TYPE EVALUATION_TYPE IS 'The type of evaluation we are using.';
-- 
-- CREATE TYPE HIT_STATUS AS ENUM (
--     'pending',
--     'accepted',
--     'rejected'
-- );
-- COMMENT ON TYPE HIT_STATUS IS 'The payment status for a HIT.';
