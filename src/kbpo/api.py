"""
Utilities connecting the web interface to database
Interfacing with database API
"""
import logging
from datetime import date, datetime
from collections import Counter
import json

from . import db
from . import defs
from .util import stuple

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_documents(corpus_tag):
    """
    Returns a list of documents with a particular corpus tag
    """
    values = db.select("""
        SELECT doc_id
        FROM document_tag
        WHERE tag=%(tag)s
        ORDER BY doc_id
        """, tag=corpus_tag)
    return [x.doc_id for x in values]

def test_get_documents():
    docs = list(get_documents("kbp2016"))
    assert len(docs) == 15001
    assert "NYT_ENG_20131216.0031" in docs

def get_document(doc_id):
    """
    Returns id, date, title and sentences for a given @doc_id
    """
    T = {
        "-LRB-": "(",
        "-RRB-": ")",
        "-LSB-": "[",
        "-RSB-": "]",
        "-LCB-": "{",
        "-RCB-": "}",
        "``": "\"",
        "''": "\"",
        "`": "'",
        }

    doc_info = db.get("""
        SELECT id, title, doc_date
        FROM document
        WHERE id = %(doc_id)s
        """, doc_id=doc_id)
    assert doc_info.id == doc_id

    sentences = []
    for row in db.select("""
            SELECT sentence_index, token_spans, words, lemmas, pos_tags, ner_tags
            FROM sentence
            WHERE doc_id = %(doc_id)s
            ORDER BY sentence_index
            """, doc_id=doc_id):
        _, token_spans, words, lemmas, pos_tags, ner_tags = row

        words = list(map(lambda w: T.get(w, w), words))
        token_spans = [(span.lower, span.upper) for span in token_spans]
        keys = ("word", "lemma", "pos_tag", "ner_tag", "span",)
        sentence = [{k:v for k, v in zip(keys, values)} for values in zip(words, lemmas, pos_tags, ner_tags, token_spans)]
        sentences.append(sentence)
    doc = {
        "id": doc_id,
        "date": doc_info.doc_date,
        "title": doc_info.title,
        "sentences": sentences,
    }
    return doc

def test_get_document():
    doc_id = "NYT_ENG_20131216.0031"
    doc = get_document(doc_id)
    assert doc["id"] == doc_id
    assert doc["title"] == "A GRAND WEEKEND OUT FOR PENNSYLVANIANS AS LEADERS GATHER IN NEW YORK"
    assert doc["date"] == date(2013, 12, 16)
    assert len(doc["sentences"]) == 25

    sentence = doc["sentences"][0]

    assert len(sentence) == 12
    assert "A GRAND WEEKEND OUT FOR PENNSYLVANIANS AS LEADERS GATHER IN NEW YORK".split() == [t["word"] for t in sentence]
    assert "a GRAND WEEKEND OUT for PENNSYLVANIANS as leader gather in new YORK".split() == [t["lemma"] for t in sentence]
    assert "DT NNP NNP NNP IN NNPS JJ NNS VBP IN JJ NNP".split() == [t["pos_tag"] for t in sentence]

    assert doc["id"] == "NYT_ENG_20131216.0031"

def get_suggested_mentions(doc_id):
    """
    Get suggested mentions for a document.
    """
    mentions = []
    for row in db.select("""
            SELECT m.span, m.gloss, m.mention_type, n.span AS canonical_span, n.gloss AS canonical_gloss, l.link_name
            FROM suggested_mention m
            JOIN suggested_mention n ON (m.doc_id = n.doc_id AND m.canonical_span = n.span)
            LEFT OUTER JOIN suggested_link l ON (n.doc_id = l.doc_id AND n.span = l.span)
            WHERE m.doc_id = %(doc_id)s
            ORDER BY m.span
            """, doc_id=doc_id):
        mention = {
            "span": (row.span.lower, row.span.upper),
            "gloss": row.gloss,
            "type": row.mention_type,
            "entity": {
                "span": (row.canonical_span.lower, row.canonical_span.upper),
                "gloss": row.canonical_gloss,
                "link": row.link_name,
                }
            }
        mentions.append(mention)
    return mentions

def test_get_suggested_mentions():
    doc_id = "NYT_ENG_20131216.0031"
    mentions = get_suggested_mentions(doc_id)
    assert len(mentions) == 73
    mention = mentions[11]
    assert mention == {
        'span': (506, 521),
        'gloss': 'Waldorf-Astoria',
        'type': 'GPE',
        'entity': {
            'span': (506, 521),
            'gloss': 'Waldorf-Astoria',
            'link': 'The_Waldorf-Astoria_Hotel',
            },
        }

def get_suggested_mention_pairs(doc_id):
    """
    Get mention pairs for suggsted mentions for a document.
    """
    mention_pairs = set()
    for row in db.select("""
            SELECT m.span AS subject, m.mention_type AS subject_type, n.span AS object, n.mention_type AS object_type
            FROM suggested_mention m, suggested_mention n
            WHERE m.doc_id = n.doc_id AND m.sentence_id = n.sentence_id
              AND m.doc_id = %(doc_id)s
              AND m.span <> n.span
              AND m.canonical_span <> n.canonical_span
              AND is_entity_type(m.mention_type)
            ORDER BY subject, object
            """, doc_id=doc_id):
        # Pick up any subject pairs that are of compatible types.
        if (row.subject_type, row.object_type) not in defs.VALID_MENTION_TYPES: continue
        # Remove pairs which have the same canonical span
        # Check that this pair doesn't already exist.
        if (row.object, row.subject) in mention_pairs: continue
        mention_pairs.add((row.subject, row.object))
    return [{"subject": (subject.lower, subject.upper), "object": (object_.lower, object_.upper)} for subject, object_ in sorted(mention_pairs)]

def test_get_suggested_mention_pairs():
    doc_id = "NYT_ENG_20131216.0031"
    pairs = get_suggested_mention_pairs(doc_id)
    assert len(pairs) == 70
    pair = pairs[0]
    assert pair['subject'] == (371, 385)
    assert pair['object'] == (360, 368)

def get_submission_mentions(submission_id, doc_id):
    """
    Get suggested mentions for a document.
    """
    mentions = []
    for row in db.select("""
            SELECT m.span, m.gloss, m.mention_type, m.canonical_span, n.gloss AS canonical_gloss, l.link_name
            FROM submission_mention m
            JOIN submission_mention n ON (m.doc_id = n.doc_id AND m.canonical_span = n.span AND m.submission_id = n.submission_id)
            LEFT OUTER JOIN submission_link l ON (n.doc_id = l.doc_id AND n.span = l.span AND n.submission_id = l.submission_id)
            WHERE m.doc_id = %(doc_id)s
              AND m.submission_id = %(submission_id)s
            ORDER BY m.span
            """, doc_id=doc_id, submission_id=submission_id):
        mention = {
            "span": (row.span.lower, row.span.upper),
            "gloss": row.gloss,
            "type": row.mention_type,
            "entity": {
                "span": (row.canonical_span.lower, row.canonical_span.upper),
                "gloss": row.canonical_gloss,
                "link": row.link_name,
                }
            }
        mentions.append(mention)
    return mentions

def test_get_submission_mentions():
    doc_id = "NYT_ENG_20131216.0031"
    mentions = get_submission_mentions(1, doc_id) # patterns
    assert len(mentions) == 10
    mention = mentions[0]
    assert mention == {
        'span' : (1261, 1278),
        'gloss': 'Edward G. Rendell',
        'type': 'PER',
        'entity': {
            'span' : (1261, 1278),
            'gloss': 'Edward G. Rendell',
            'link': 'Ed_Rendell',
            },
        }

def get_evaluation_mentions(doc_id):
    """
    Get mention pairs from exhaustive mentions for a document.
    """
    mentions = []
    for i, row in enumerate(db.select("""
            SELECT m.span, m.gloss, m.mention_type, n.span AS canonical_span, n.gloss AS canonical_gloss, l.link_name
            FROM evaluation_mention m
            JOIN evaluation_mention n ON (m.doc_id = n.doc_id AND m.canonical_span = n.span)
            LEFT OUTER JOIN evaluation_link l ON (n.doc_id = l.doc_id AND n.span = l.span)
            WHERE m.doc_id = %(doc_id)s
            ORDER BY m.span
            """, doc_id=doc_id)):
        mention = {
            "id": i,
            "span": (row.span.lower, row.span.upper),
            "gloss": row.gloss,
            "type": row.mention_type,
            "entity": {
                "span": (row.canonical_span.lower, row.canonical_span.upper),
                "gloss": row.canonical_gloss,
                "link": row.link_name,
                }
            }
        mentions.append(mention)
    return mentions

def test_get_evaluation_mentions():
    doc_id = "NYT_ENG_20130726.0208"
    mentions = get_evaluation_mentions(doc_id)
    assert len(mentions) == 118
    mention = mentions[10]
    assert mention == {
        'id': 10,
        'span': (787, 792),
        'gloss': 'Hamas',
        'type': 'ORG',
        'entity': {
            'span': (787, 792),
            'gloss': 'Hamas',
            'link': 'Hamas',
            },
        }

def get_submission_mention_pair(submission_id, doc_id, subject_id, object_id):
    row = db.get("""
        SELECT r.doc_id, r.subject, r.object, 
               r.subject_type, r.object_type,
               r.subject_gloss, r.object_gloss,
               r.subject_canonical_gloss, r.object_canonical_gloss,
               r.subject_canonical, r.object_canonical,
               r.subject_entity, r.object_entity
        FROM submission_entity_relation r
        WHERE r.submission_id = %(submission_id)s
          AND r.doc_id = %(doc_id)s
          AND r.subject = %(subject_id)s
          AND r.object = %(object_id)s
        ;
        """, submission_id=submission_id, doc_id=doc_id, subject_id=db.Int4NumericRange(*subject_id), object_id=db.Int4NumericRange(*object_id))

    if row.subject_canonical_gloss.startswith("gloss:"):
        subject_canonical_gloss = row.subject_canonical_gloss[len("gloss:"):]
    if row.object_canonical_gloss.startswith("gloss:"):
        object_canonical_gloss = row.object_canonical_gloss[len("gloss:"):]

    subject = {
        "span": stuple(row.subject),
        "gloss": row.subject_gloss,
        "type": row.subject_type,
        "entity": {
            "span": stuple(row.subject_canonical),
            "gloss": subject_canonical_gloss,
            "type": row.subject_type,
            "link": row.subject_entity,
            }
        }
    object_ = {
        "span": stuple(row.object),
        "gloss": row.object_gloss,
        "type": row.object_type,
        "entity": {
            "span": stuple(row.object_canonical),
            "gloss": object_canonical_gloss,
            "type": row.object_type,
            "link": row.object_entity,
            }
        }
    # Flip types to be nice to Javascript.
    if row.subject_type == 'ORG' and row.object_type == 'PER':
        subject, object_ = object_, subject
    elif row.subject_type == 'GPE':
        subject, object_ = object_, subject

    return subject, object_

def test_get_submission_mention_pair():
    subject, object_ = get_submission_mention_pair(25,'ENG_NW_001278_20130414_F000124GV', (662,688), (615,617))

    assert subject == {
        'entity': {
            'link': ':wilmer_barrientos_f096023f',
            'span': (586, 603),
            'type': 'PER',
            'gloss': 'Wilmer Barrientos'
            },
        'span': (615, 617),
        'type': 'PER',
        'gloss': 'he'
        }
    assert object_ == {'entity': {'link': ':national_electoral_council__venezuela__5dae2c88', 'span': (662, 688), 'type': 'ORG', 'gloss': 'National Electoral Council'}, 'span': (662, 688), 'type': 'ORG', 'gloss': 'National Electoral Council'}

def get_evaluation_mention_pairs(doc_id):
    """
    Get mention pairs from exhaustive mentions for a document.
    """
    mention_pairs = set()
    for row in db.select("""
            SELECT m.span AS subject, m.mention_type AS subject_type, n.span AS object, n.mention_type AS object_type
            FROM evaluation_mention m, evaluation_mention n, sentence s
            WHERE m.doc_id = n.doc_id AND m.span <> n.span
              AND m.doc_id = s.doc_id AND m.span <@ s.span AND n.span <@ s.span
              AND m.doc_id = %(doc_id)s
              AND is_entity_type(m.mention_type)
            ORDER BY subject, object
            """, doc_id=doc_id):
        # Pick up any subject pairs that are of compatible types.
        if (row.subject_type, row.object_type) not in defs.VALID_MENTION_TYPES: continue
        # Check that this pair doesn't already exist.
        if (row.object, row.subject) in mention_pairs: continue
        mention_pairs.add((row.subject, row.object))
    return [{"subject": (subject.lower, subject.upper), "object": (object_.lower, object_.upper)} for subject, object_ in sorted(mention_pairs)]

def test_get_evaluation_mention_pairs():
    doc_id = "NYT_ENG_20130726.0208"
    pairs = get_evaluation_mention_pairs(doc_id)
    assert len(pairs) == 238
    pair = pairs[5]
    assert pair['subject'] == (628, 642)
    assert pair['object'] == (568, 574)

def get_evaluation_relations(doc_id):
    """
    Get relations for a document.
    """
    relations = []
    for row in db.select("""
            SELECT DISTINCT ON (subject, object)
            r.subject, r.subject_type, r.relation, r.object, r.object_type
            FROM evaluation_entity_relation r
            WHERE r.doc_id = %(doc_id)s
            ORDER BY r.subject, r.object, r.relation
            """, doc_id=doc_id):
        if not defs.is_canonical_relation(row.relation, row.subject_type, row.object_type):
            continue

        relation = {
            "subject": (row.subject.lower, row.subject.upper),
            "relation": row.relation,
            "object": (row.object.lower, row.object.upper),
            }
        relations.append(relation)
    return relations

def test_get_evaluation_relations():
    doc_id = "NYT_ENG_20130726.0208"
    relations = get_evaluation_relations(doc_id)
    assert len(relations) == 42
    relation = relations[0]
    assert relation['subject'] == (172, 177)
    assert relation['object'] == (223, 228)
    assert relation['relation'] == 'per:place_of_residence'

def get_submissions(corpus_tag):
    return db.select("""SELECT * FROM submission WHERE corpus_tag=%(corpus_tag)s AND active ORDER BY id""", corpus_tag=corpus_tag)

def test_get_submissions():
    tag = 'kbp2016'
    assert [s.name for s in get_submissions(tag)] == ["patterns", "supervised", "rnn"]

def get_submission(submission_id):
    return db.get("""SELECT id, updated, name, corpus_tag, details FROM submission WHERE id=%(submission_id)s""", submission_id=submission_id)

def test_get_submission():
    submission_id = 1
    submission = get_submission(submission_id)
    assert submission.name == "patterns"
    assert submission.corpus_tag == "kbp2016"

def get_submission_relations(doc_id, submission_id):
    """
    Get suggested mentions for a document.
    """
    relations = []
    for row in db.select("""
            SELECT subject, relation, object, provenances, confidence
            FROM submission_relation
            WHERE doc_id = %(doc_id)s
              AND submission_id = %(submission_id)s
            ORDER BY subject
            """, doc_id=doc_id, submission_id=submission_id):
        assert len(row.provenances) > 0, "Invalid submission entry does not have any provenances"
        relation = {
            "subject": (row.subject.lower, row.subject.upper),
            "relation": row.relation,
            "object": (row.object.lower, row.object.upper),
            "provenance": (row.provenances[0].lower, row.provenances[0].upper), # Only use the first provenance.
            "confidence": row.confidence,
            }
        relations.append(relation)
    return relations

def test_get_submission_relations():
    doc_id = "NYT_ENG_20131216.0031"
    relations = get_submission_relations(doc_id, 1)
    assert len(relations) == 5
    relation = relations[0]

    assert relation == {
        "subject": (1261,1278),
        "relation": 'per:title',
        "object": (1300,1308),
        "provenance": (1196, 1338),
        "confidence": 1.
        }

def get_submission_relation_list(submission_id, count=1):
    """
    Get suggested mentions for a document.
    """
    ret = []
    for row in db.select("""
            SELECT doc_id, subject, subject_type, relation, object, object_type, provenances, confidence
            FROM submission_entity_relation r
            WHERE r.submission_id = %(submission_id)s
            ORDER BY doc_id, subject, object
            LIMIT %(count)s
            """, submission_id=submission_id, count=count):
        assert len(row.provenances) > 0, "Invalid submission entry does not have any provenances"

        subject, _, relation, object_, _ = defs.standardize_relation(
            row.subject, row.subject_type, row.relation, row.object, row.object_type)

        relation = {
            "doc_id": row.doc_id,
            "subject": (subject.lower, subject.upper),
            "relation": relation,
            "object": (object_.lower, object_.upper),
            "provenance": (row.provenances[0].lower, row.provenances[0].upper), # Only use the first provenance.
            "confidence": row.confidence,
            }
        ret.append(relation)

        if len(ret) == count: break
    return ret


                    

def insert_assignment(
        assignment_id, hit_id, worker_id,
        worker_time, comments, response,
        state="pending-extraction", created=datetime.now()):
    with db.CONN:
        with db.CONN.cursor() as cur:
            batch_id = db.get("""SELECT batch_id FROM mturk_hit WHERE id = %(hit_id)s;""", hit_id=hit_id, cur=cur)
            existing_response = db.select("SELECT * FROM mturk_assignment WHERE id = %(assignment_id)s;", assignment_id=assignment_id, cur=cur)
            if len(existing_response) >= 1:
                assert len(existing_response) == 1, "More than 1 assignment stored for an assignment_id"
                existing_response = existing_response[0]
                existing_response_json = json.dumps(existing_response.response, sort_keys=True)
                response_json = json.dumps(response, sort_keys=True)
                assert existing_response_json == response_json, "Existing response %s doesn't match with the one being inserted %s"%(existing_response_json, response_json)
                if state == 'submitted':
                    state = existing_response.state
                else:
                    #states could be approved or rejected
                    pass
            db.execute("""
                INSERT INTO mturk_assignment (id, hit_id, batch_id, worker_id, created, worker_time, response, comments, state)
                VALUES (%(assignment_id)s, %(hit_id)s, %(batch_id)s, %(worker_id)s, %(created)s, %(worker_time)s, %(response)s, %(comments)s, %(state)s) ON CONFLICT (id)  DO UPDATE SET state=%(state)s""",
                       assignment_id=assignment_id,
                       hit_id=hit_id,
                       batch_id=batch_id,
                       worker_id= worker_id,
                       created= created,
                       worker_time=int(float(worker_time)),
                       response=db.Json(response),
                       comments=comments,
                       state=state)
    return assignment_id

def get_hits(limit=None):
    if limit is None:
        return db.select("""SELECT * FROM mturk_hit ORDER BY id""")
    else:
        return db.select("""SELECT * FROM mturk_hit ORDER BY id LIMIT %(limit)s""", limit=limit)

def get_hit(hit_id):
    return db.get("""SELECT * FROM mturk_hit WHERE hit_id=%(hit_id)s""", hit_id=hit_id)

def get_task_params(hit_id):
    """
    Gets parameters from the task.
    """
    return db.get("""
        SELECT params 
        FROM mturk_hit h 
        JOIN evaluation_question q ON (h.question_batch_id = q.batch_id AND h.question_id = q.id)
        WHERE h.id=%(hit_id)s""", hit_id=hit_id).params

def get_submission_entries(submission_id):
    """
    Get entries from a submission that have been evaluated by Turk.
    """
    distinct = set()
    entries = []
    for i, row in enumerate(db.select("""
        SELECT doc_id,
               title,
               corpus_tag,
               sentence,
               sentence_span,
               subject,
               subject_type,
               subject_gloss,
               subject_canonical_gloss,
               object,
               object_type,
               object_gloss,
               object_canonical_gloss,

               subject_entity,
               subject_entity_gold,
               subject_entity_correct,

               object_entity,
               object_entity_gold,
               object_entity_correct,

               predicate_name,
               predicate_gold,
               predicate_correct,
               correct

        FROM submission_entries
        WHERE submission_id = %(submission_id)s
          AND subject_type_match AND object_type_match
          AND subject_entity_match AND object_entity_match
        ORDER BY doc_id, subject, object
        """, submission_id=submission_id)):

        # Only keep non-inverted relations.
        if not defs.is_canonical_relation(row.predicate_name, row.subject_type, row.object_type):
            continue # skip because the inverted relation will come along.
        if not defs.is_canonical_relation(row.predicate_gold, row.subject_type, row.object_type):
            continue # skip because the inverted relation will come along.

        key = row.doc_id, stuple(row.subject), stuple(row.object)
        key = key[0], min(key[1], key[2]), max(key[1], key[2])
        if key in distinct:
            continue
        distinct.add(key)

        entry = {
            "doc_id": row.doc_id,
            "corpus_tag": row.corpus_tag,
            "title": row.title,
            "sentence": row.sentence,
            "subject": {
                # Relative to sentences
                "span": [row.subject.lower - row.sentence_span.lower, row.subject.upper  - row.sentence_span.lower],
                "type": row.subject_type,
                "gloss": row.subject_gloss,
                "entity": {
                    "type": row.subject_type,
                    "gloss": row.subject_canonical_gloss,
                    "link": row.subject_entity,
                    "linkGold": row.subject_entity_gold,
                    "linkCorrect": row.subject_entity_correct,
                    },
                },
            "object": {
                # Relative to sentences
                "span": [row.object.lower - row.sentence_span.lower, row.object.upper  - row.sentence_span.lower],
                "type": row.object_type,
                "gloss": row.object_gloss,
                "entity": {
                    "type": row.object_type,
                    "gloss": row.object_canonical_gloss,
                    "link": row.object_entity,
                    "linkGold": row.object_entity_gold,
                    "linkCorrect": row.object_entity_correct,
                    },
                },
            "predicate": {
                "name": row.predicate_name,
                "gold": row.predicate_gold,
                "isCorrect": row.predicate_correct,
                },
            "isCorrect": row.correct,
            }
        entries.append(entry)
    return entries

def test_get_submission_entries():
    submission_id=1
    entries = get_submission_entries(submission_id)
    assert len(entries) == 1450
    entry = entries[0]
    assert entry == {
        'corpus_tag': 'kbp2016',
        'doc_id': 'ENG_NW_001278_20130111_F00013FIO',
        'title': 'Argentine striker Barcos re-signs with Palmeiras',
        'sentence': 'Argentine striker Barcos re-signs with Palmeiras',
        'subject': {
            'gloss': 'Barcos',
            'entity': {
                'linkCorrect': True,
                'gloss': 'gloss:Barcos',
                'link': 'Hernán_Barcos',
                'linkGold': 'gloss:Barcos',
                'type': 'PER'
                },
            'span': [18, 24],
            'type': 'PER'
            },
        'object': {
            'gloss': 'striker',
            'entity': {
                'linkCorrect': True,
                'gloss': 'gloss:striker',
                'link': 'gloss:striker',
                'linkGold': 'gloss:striker',
                'type': 'TITLE'},
            'span': [10, 17],
            'type': 'TITLE'
            },
        'predicate': {
            'name': 'per:title',
            'isCorrect': True,
            'gold': 'per:title'
            },
        'isCorrect': True,
        }

def get_leaderboard():
    """Get scores for all submissions"""
    entries = []
    for row in db.select("""
        WITH latest_scores AS (SELECT DISTINCT ON (submission_id)
            submission_id, score, left_interval, right_interval
            FROM submission_score
            WHERE score_type = 'entity_relation'
            ORDER BY submission_id, updated DESC)
        SELECT 
        u.id AS user_id,
        u.affiliation AS user_affiliation,
        sub.id, 
        sub.updated, 
        sub.name, 
        sub.corpus_tag, 
        sub.details, 
        sc.score,
        sc.left_interval,
        sc.right_interval 
        FROM latest_scores AS sc 
        JOIN submission AS sub ON (sub.id = sc.submission_id AND sub.active)
        JOIN web_submissionuser subuser ON (subuser.submission_id = sub.id)
        JOIN web_user u ON (subuser.user_id = u.id)
        ORDER BY (sc.score).f1 DESC;"""):
        entry = {
            'user_id': row.user_id,
            'user_affiliation': row.user_affiliation,
            'id': row.id,
            'name': row.name,
            'details': row.details,
            'timestamp': row.updated,
            'corpus': row.corpus_tag,
            'P': row.score.precision, 'R': row.score.recall, 'F1': row.score.f1,
            'P-range': [row.left_interval.precision, row.right_interval.precision],
            'R-range': [row.left_interval.recall, row.right_interval.recall],
            'F1-range': [row.left_interval.f1, row.right_interval.f1],
            }
        entries.append(entry)
    return {'submissions': entries}

def test_get_leaderboard():
    obj = get_leaderboard()
    assert len(obj) > 0

def get_corpus_listing(corpus_tag):
    """
    List documents from the corpus, with summaries of #entities,
    #relations.
    """
    entries = []
    for row in db.select("""
        WITH entity_counts AS (
            SELECT t.doc_id, COUNT(*)
            FROM document_tag t,
                 evaluation_mention m
            WHERE m.doc_id = t.doc_id
              AND t.tag = %(corpus_tag)s
              GROUP BY t.doc_id),
             relation_counts AS (
            SELECT t.doc_id, COUNT(*)
            FROM document_tag t,
                 evaluation_relation r
            WHERE r.doc_id = t.doc_id
              AND t.tag = %(corpus_tag)s
              GROUP BY t.doc_id)
        SELECT d.id, d.title, d.doc_date, e.count AS entity_count, r.count AS relation_count
        FROM document d
        JOIN document_tag t ON (d.id = t.doc_id AND t.tag = %(corpus_tag)s)
        JOIN entity_counts e ON (d.id = e.doc_id)
        JOIN relation_counts r ON (d.id = r.doc_id)
        ORDER BY e.count DESC, r.count DESC, d.id
        """, corpus_tag=corpus_tag):
        entry = {
            "docId": row.id,
            "title": row.title,
            "date": row.doc_date,
            "entityCount": row.entity_count,
            "relationCount": row.relation_count,
            }
        entries.append(entry)
    return entries

def test_get_corpus_listing():
    corpus_tag='kbp2016'
    entries = get_corpus_listing(corpus_tag)
    assert len(entries) == 1232
    entry = entries[0]
    assert entry == {
        'docId': 'ENG_NW_001278_20130316_F00012OME',
        'title': "3rd LD Writethru-Xinhua Insight: China's new leadership takes shape amid high expectations",
        "date": date(2013, 3, 16),
        "entityCount": 72,
        "relationCount": 119,
        }

def upload_submission(submission_id, mfile):
    with db.CONN:
        with db.CONN.cursor() as cur:
            # TODO: What about husk sample_batches created this way?
            db.execute("""DELETE FROM submission_sample WHERE submission_id=%(submission_id)s""", cur=cur, submission_id=submission_id)
            db.execute("""DELETE FROM submission_relation WHERE submission_id=%(submission_id)s""", cur=cur, submission_id=submission_id)
            db.execute("""DELETE FROM submission_link WHERE submission_id=%(submission_id)s""", cur=cur, submission_id=submission_id)
            db.execute("""DELETE FROM submission_mention WHERE submission_id=%(submission_id)s""", cur=cur, submission_id=submission_id)

            # Create the submission
            mentions, links, relations = [], [], []

            def _p(prov):
                return db.Int4NumericRange(prov.begin, prov.end)


            for mention_id in mfile.mention_ids:
                mention_type, gloss, canonical_id = mfile.get_type(mention_id), mfile.get_gloss(mention_id), mfile.get_cmention(mention_id)
                mention_id, canonical_id = mention_id, canonical_id
                doc_id = mention_id.doc_id
                mentions.append((submission_id, doc_id, _p(mention_id), _p(canonical_id), mention_type, gloss))
            for row in mfile.links:
                mention_id = row.subj
                doc_id = mention_id.doc_id
                link_name = row.obj
                weight = row.weight
                links.append((submission_id, doc_id, _p(mention_id), link_name, weight))
            for row in mfile.relations:
                subject_id = row.subj
                object_id = row.obj
                doc_id = subject_id.doc_id

                relation = row.reln
                provs = list(row.prov) if row.prov else []
                weight = row.weight
                relations.append((submission_id, doc_id, _p(subject_id), _p(object_id), relation, [_p(prov) for prov in provs], weight))

            # mentions
            db.execute_values(cur, """INSERT INTO submission_mention (submission_id, doc_id, span, canonical_span, mention_type, gloss) VALUES %s """, mentions)

            # links
            db.execute_values(cur, """INSERT INTO submission_link (submission_id, doc_id, span, link_name, confidence) VALUES %s """, links)

            # relations
            db.execute_values(cur, """INSERT INTO submission_relation (submission_id, doc_id, subject, object, relation, provenances, confidence) VALUES %s """, relations)

            # refresh materialized views.
            cur.execute("""REFRESH MATERIALIZED VIEW submission_mention_link""")
            cur.execute("""REFRESH MATERIALIZED VIEW submission_entity_relation""")
            cur.execute("""REFRESH MATERIALIZED VIEW submission_statistics""")
            cur.execute("""REFRESH MATERIALIZED VIEW submission_relation_counts""")
            cur.execute("""REFRESH MATERIALIZED VIEW submission_entity_counts""")
            cur.execute("""REFRESH MATERIALIZED VIEW submission_entity_relation_counts""")

def get_question_batch(question_batch_id):
    return db.get("""
        SELECT id, created, batch_type, corpus_tag, description FROM evaluation_batch
        WHERE id = %(batch_id)s
        """, batch_id=question_batch_id)

def get_questions(question_batch_id):
    return db.select("""
        SELECT id, params from evaluation_question
        WHERE batch_id = %(batch_id)s
        ORDER BY id
        """, batch_id=question_batch_id)

def get_submission_sample_batches(submission_id):
    return [row.id for row in db.select("""
        SELECT b.id
        FROM sample_batch b
        WHERE submission_id = %(submission_id)s
        ORDER BY created DESC
        """, submission_id=submission_id)]

def get_samples(sample_batch_id):
    return db.select("""
        SELECT submission_id, doc_id, subject, object
        FROM submission_sample
        WHERE batch_id = %(batch_id)s
        """, batch_id=sample_batch_id)

def get_evaluation_batch_status(batch_id):
    # Get's the summary of states of its questions
    stats = db.select("""
        SELECT state, COUNT(*) AS count
        FROM evaluation_question
        WHERE batch_id=%(batch_id)s
        GROUP BY state
        """, batch_id=batch_id)
    return Counter({state: count for state, count in stats})

def get_evaluation_batch(batch_id):
    return db.get("""
        SELECT id, corpus_tag, batch_type, description
        FROM evaluation_batch
        WHERE id=%(batch_id)s
        """, batch_id=batch_id)

def get_mturk_batch_status(batch_id):
    # Get's the summary of states of its questions
    stats = db.select("""
        SELECT state, COUNT(*) AS count
        FROM mturk_hit
        WHERE batch_id=%(batch_id)s
        GROUP BY state
        """, batch_id=batch_id)
    return Counter({state: count for state, count in stats})

