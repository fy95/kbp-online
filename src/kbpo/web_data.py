#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilities to handle conversion and interaction of data in JSON
"""
import json
import logging

from . import db
from .defs import Provenance, MentionInstance, CanonicalMentionInstance, LinkInstance, RelationInstance
from .schema import EvaluationMentionResponse, EvaluationLinkResponse, EvaluationRelationResponse

logger = logging.getLogger(__name__)

def parse_selective_relations_response(question, responses):
    mentions, canonical_mentions, links, relations = [], [], [], []
    for response in responses:
        doc_id = question["doc_id"]
        subject_id = Provenance(doc_id, response["subject"]["doc_char_begin"], response["subject"]["doc_char_end"])
        subject_canonical_id = Provenance(doc_id, response["subject"]["entity"]["doc_char_begin"], response["subject"]["entity"]["doc_char_end"])
        object_id = Provenance(doc_id, response["object"]["doc_char_begin"], response["object"]["doc_char_end"])
        object_canonical_id = Provenance(doc_id, response["object"]["entity"]["doc_char_begin"], response["object"]["entity"]["doc_char_end"])

        if "canonicalCorrect" in response["subject"]["entity"]:
            canonical_mentions.append(CanonicalMentionInstance(subject_id, subject_canonical_id, 1.0 if response["subject"]["entity"]["canonicalCorrect"] == "Yes" else 0.0))
        if "canonicalCorrect" in response["object"]["entity"]:
            canonical_mentions.append(CanonicalMentionInstance(object_id,  object_canonical_id, 1.0 if response["object"]["entity"]["canonicalCorrect"] == "Yes" else 0.0))
        if "linkCorrect" in response["subject"]["entity"]:
            links.append(LinkInstance(subject_id, response["subject"]["entity"]["link"], 1.0 if response["subject"]["entity"]["linkCorrect"] == "Yes" else 0.0))
        if "linkCorrect" in response["object"]["entity"]:
            links.append(LinkInstance(object_id, response["object"]["entity"]["link"], 1.0 if response["object"]["entity"]["linkCorrect"] == "Yes" else 0.0))

        relations.append(RelationInstance(subject_id, object_id, response["relation"], 1.0))
    return sorted(set(mentions)), sorted(set(canonical_mentions)), sorted(set(links)), sorted(set(relations))

def test_parse_selective_relations_response():
    # My output could be one of the following cases:
    # - the mention could be wrong. (TODO: how are we handling this?)
    # - the linking could be wrong.
    # - the relation could be wrong.
    question = {"mention_2": ["NYT_ENG_20130911.0085", "2803", "2809"], "doc_id": "NYT_ENG_20130911.0085", "batch_type": "selective_relations", "mention_1": ["NYT_ENG_20130911.0085", "2778", "2783"]}
    response = {"subject":{"gloss":"Mukesh","type":{"idx":0,"name":"PER","gloss":"Person","icon":"fa-user","linking":"wiki-search"},"doc_char_begin":2803,"doc_char_end":2809,"entity":{"gloss":"Mukesh","link":"Mukesh_Ambani","doc_char_begin":2803,"doc_char_end":2809,"canonicalCorrect":"Yes","linkCorrect":"No"}},"relation":"per:sibling","object":{"gloss":"Singh","type":{"idx":0,"name":"PER","gloss":"Person","icon":"fa-user","linking":"wiki-search"},"doc_char_begin":2778,"doc_char_end":2783,"entity":{"gloss":"Ram Singh","link":"Ram_Singh","doc_char_begin":1703,"doc_char_end":1712,"canonicalCorrect":"Yes","linkCorrect":"No"}}}
    subject_id = Provenance('NYT_ENG_20130911.0085', 2803, 2809)
    subject_canonical_id = Provenance('NYT_ENG_20130911.0085', 2803, 2809)
    object_id = Provenance('NYT_ENG_20130911.0085', 2778, 2783)
    object_canonical_id = Provenance('NYT_ENG_20130911.0085', 1703, 1712)

    mentions_, canonical_mentions_, links_, relations_ = parse_selective_relations_response(question, response)
    assert mentions_ == []
    assert canonical_mentions_ == [CanonicalMentionInstance(subject_id, subject_canonical_id, 1.0), CanonicalMentionInstance(object_id, object_canonical_id, 1.0)]
    assert links_ == [LinkInstance(subject_id, "Mukesh_Ambani", 0.0), LinkInstance(object_id, "Ram_Singh", 0.0)]
    assert relations_ == [RelationInstance(subject_id, object_id, "per:sibling", 1.0)]

def parse_exhaustive_relations_response(question, responses):
    mentions, canonical_mentions, links = [], [], []
    relations = []
    doc_id = question["doc_id"]
    for response in responses:
        subject = Provenance(doc_id, response["subject"]["doc_char_begin"], response["subject"]["doc_char_end"])
        object_ = Provenance(doc_id, response["object"]["doc_char_begin"], response["object"]["doc_char_end"])
        relation = RelationInstance(subject, object_, response["relation"], 1.0)
        relations.append(relation)
    return sorted(set(mentions)), sorted(set(canonical_mentions)), sorted(set(links)), sorted(set(relations))

def test_parse_exhaustive_relations_response():
    question = {"doc_id": "ENG_NW_001278_20130216_F00011Q88", "batch_type": "exhaustive_relations"}
    response = [{"subject":{"gloss":"\xa0Ahmed\xa0Omar","type":{"idx":0,"name":"PER","gloss":"Person","icon":"fa-user","linking":"wiki-search"},"doc_char_begin":438,"doc_char_end":448,"entity":{"gloss":"\xa0Ahmed\xa0Omar","link":"","doc_char_begin":438,"doc_char_end":448}},"relation":"per:employee_or_member_of","object":{"gloss":"\xa0Health\xa0Ministry","type":{"idx":1,"name":"ORG","gloss":"Organization","icon":"fa-building","linking":"wiki-search"},"doc_char_begin":412,"doc_char_end":427,"entity":{"gloss":"\xa0Health\xa0Ministry","link":"Ministry_of_Health_(Egypt)","doc_char_begin":412,"doc_char_end":427}}},{"subject":{"gloss":"\xa0al-Jamaa\xa0al-\xa0Islamiya","type":{"idx":1,"name":"ORG","gloss":"Organization","icon":"fa-building","linking":"wiki-search"},"doc_char_begin":983,"doc_char_end":1004,"entity":{"gloss":"\xa0al-Jamaa\xa0al-\xa0Islamiya","link":"Al-Jama%27a_al-Islamiyya","doc_char_begin":983,"doc_char_end":1004}},"relation":"org:member_of","object":{"gloss":"\xa0Construction\xa0and\xa0Development\xa0Party","type":{"idx":1,"name":"ORG","gloss":"Organization","icon":"fa-building","linking":"wiki-search"},"doc_char_begin":1031,"doc_char_end":1065,"entity":{"gloss":"\xa0Construction\xa0and\xa0Development\xa0Party","link":"Building_and_Development_Party","doc_char_begin":1031,"doc_char_end":1065}}},{"subject":{"gloss":"\xa0Mohamed","type":{"idx":0,"name":"PER","gloss":"Person","icon":"fa-user","linking":"wiki-search"},"doc_char_begin":1229,"doc_char_end":1236,"entity":{"gloss":"\xa0Mohamed","link":"Mohamed_Morsi","doc_char_begin":1229,"doc_char_end":1236}},"relation":"per:title","object":{"gloss":"\xa0President","type":{"idx":4,"name":"TITLE","gloss":"Title","icon":"fa-id-card-o","linking":""},"doc_char_begin":1219,"doc_char_end":1228,"entity":{"gloss":"\xa0President","link":"","doc_char_begin":1219,"doc_char_end":1228}}},{"subject":{"gloss":"\xa0Morsi","type":{"idx":0,"name":"PER","gloss":"Person","icon":"fa-user","linking":"wiki-search"},"doc_char_begin":1237,"doc_char_end":1242,"entity":{"gloss":"\xa0Mohamed","link":"Mohamed_Morsi","doc_char_begin":1229,"doc_char_end":1236}},"relation":"per:title","object":{"gloss":"\xa0President","type":{"idx":4,"name":"TITLE","gloss":"Title","icon":"fa-id-card-o","linking":""},"doc_char_begin":1219,"doc_char_end":1228,"entity":{"gloss":"\xa0President","link":"","doc_char_begin":1219,"doc_char_end":1228}}}]

    mentions, canonical_mentions, links, relations = parse_exhaustive_relations_response(question, response)
    assert len(mentions) == 0
    assert len(canonical_mentions) == 0
    assert len(links) == 0
    assert len(relations) == 4
    assert relations[0].subject_id == Provenance("ENG_NW_001278_20130216_F00011Q88", 438, 448)
    assert relations[0].object_id == Provenance("ENG_NW_001278_20130216_F00011Q88", 412, 427)
    assert relations[0].relation == "per:employee_or_member_of"

def parse_exhaustive_entities_response(question, response):
    doc_id = question["doc_id"]
    mentions = []
    canonical_mentions = []
    links = []
    relations = []
    for entity in response:
        id_ = Provenance(doc_id, entity["doc_char_begin"], entity["doc_char_end"])
        type_ = entity["type"]["name"]
        gloss = entity["gloss"]

        mention = MentionInstance(id_, type_, gloss)
        canonical_id = Provenance(doc_id, entity["entity"]["doc_char_begin"], entity["entity"]["doc_char_end"])
        canonical_mention = CanonicalMentionInstance(id_, canonical_id, 1.0)

        mentions.append(mention)
        canonical_mentions.append(canonical_mention)

        if id_ == canonical_id:
            link = LinkInstance(canonical_id, entity["entity"]["link"], 1.0)
            links.append(link)
    return sorted(set(mentions)), sorted(set(canonical_mentions)), sorted(set(links)), sorted(set(relations))

def test_parse_exhaustive_entities_response():
    question = {"doc_id": "NYT_ENG_20130911.0085", "batch_type": "exhaustive_entities"}
    response = [{"gloss": "China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 106, "doc_char_begin": 101, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 212, "doc_char_begin": 207, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 308, "doc_char_begin": 303, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 524, "doc_char_begin": 519, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 896, "doc_char_begin": 891, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 1232, "doc_char_begin": 1227, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "China", "entity": {"gloss": "China", "doc_char_end": 106, "link": "China", "doc_char_begin": 101}, "doc_char_end": 1308, "doc_char_begin": 1303, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "BEIJING", "entity": {"gloss": "BEIJING", "doc_char_end": 282, "link": "Beijing", "doc_char_begin": 275}, "doc_char_end": 282, "doc_char_begin": 275, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0May\u00a015", "entity": {"gloss": "\u00a0May\u00a015", "doc_char_end": 290, "link": "2001-05-15", "doc_char_begin": 284}, "doc_char_end": 290, "doc_char_begin": 284, "type": {"gloss": "Date", "idx": 3, "linking": "date-picker", "name": "DATE", "icon": "fa-calendar"}}, {"gloss": "Xinhua", "entity": {"gloss": "Xinhua", "doc_char_end": 298, "link": "Xinhua_News_Agency", "doc_char_begin": 292}, "doc_char_end": 298, "doc_char_begin": 292, "type": {"gloss": "Organization", "idx": 1, "linking": "wiki-search", "name": "ORG", "icon": "fa-building"}}, {"gloss": "\u00a0Ministry\u00a0of\u00a0Public\u00a0Security", "entity": {"gloss": "\u00a0Ministry\u00a0of\u00a0Public\u00a0Security", "doc_char_end": 338, "link": "Ministry_of_Public_Security_(China)", "doc_char_begin": 311}, "doc_char_end": 338, "doc_char_begin": 311, "type": {"gloss": "Organization", "idx": 1, "linking": "wiki-search", "name": "ORG", "icon": "fa-building"}}, {"gloss": "\u00a0MPS", "entity": {"gloss": "\u00a0Ministry\u00a0of\u00a0Public\u00a0Security", "doc_char_end": 338, "link": "Ministry_of_Public_Security_(China)", "doc_char_begin": 311}, "doc_char_end": 459, "doc_char_begin": 456, "type": {"gloss": "Organization", "idx": 1, "linking": "wiki-search", "name": "ORG", "icon": "fa-building"}}, {"gloss": "\u00a0MPS", "entity": {"gloss": "\u00a0Ministry\u00a0of\u00a0Public\u00a0Security", "doc_char_end": 338, "link": "Ministry_of_Public_Security_(China)", "doc_char_begin": 311}, "doc_char_end": 788, "doc_char_begin": 785, "type": {"gloss": "Organization", "idx": 1, "linking": "wiki-search", "name": "ORG", "icon": "fa-building"}}, {"gloss": "\u00a0Police\u00a0Force\u00a0of\u00a0Myanmar", "entity": {"gloss": "\u00a0Police\u00a0Force\u00a0of\u00a0Myanmar", "doc_char_end": 376, "link": "", "doc_char_begin": 353}, "doc_char_end": 376, "doc_char_begin": 353, "type": {"gloss": "Organization", "idx": 1, "linking": "wiki-search", "name": "ORG", "icon": "fa-building"}}, {"gloss": "\u00a0Nansan-Lougai", "entity": {"gloss": "\u00a0Nansan-Lougai", "doc_char_end": 495, "link": "", "doc_char_begin": 482}, "doc_char_end": 495, "doc_char_begin": 482, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Yunnan\u00a0Province", "entity": {"gloss": "\u00a0Yunnan\u00a0Province", "doc_char_end": 542, "link": "Yunnan_Province,_Republic_of_China", "doc_char_begin": 527}, "doc_char_end": 542, "doc_char_begin": 527, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Yunnan", "entity": {"gloss": "\u00a0Yunnan\u00a0Province", "doc_char_end": 542, "link": "Yunnan_Province,_Republic_of_China", "doc_char_begin": 527}, "doc_char_end": 709, "doc_char_begin": 703, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Kokang", "entity": {"gloss": "\u00a0Yunnan\u00a0Province", "doc_char_end": 542, "link": "Yunnan_Province,_Republic_of_China", "doc_char_begin": 527}, "doc_char_end": 572, "doc_char_begin": 566, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Yunnan", "entity": {"gloss": "\u00a0Yunnan\u00a0Province", "doc_char_end": 542, "link": "Yunnan_Province,_Republic_of_China", "doc_char_begin": 527}, "doc_char_end": 1220, "doc_char_begin": 1214, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Yunnan", "entity": {"gloss": "\u00a0Yunnan\u00a0Province", "doc_char_end": 542, "link": "Yunnan_Province,_Republic_of_China", "doc_char_begin": 527}, "doc_char_end": 1431, "doc_char_begin": 1425, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Ruili", "entity": {"gloss": "\u00a0Ruili", "doc_char_end": 717, "link": "Ruili", "doc_char_begin": 712}, "doc_char_end": 717, "doc_char_begin": 712, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Longchuan", "entity": {"gloss": "\u00a0Longchuan", "doc_char_end": 731, "link": "Longchuan", "doc_char_begin": 722}, "doc_char_end": 731, "doc_char_begin": 722, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a02007", "entity": {"gloss": "\u00a02007", "doc_char_end": 755, "link": "2007-12-XX", "doc_char_begin": 751}, "doc_char_end": 755, "doc_char_begin": 751, "type": {"gloss": "Date", "idx": 3, "linking": "date-picker", "name": "DATE", "icon": "fa-calendar"}}, {"gloss": "\u00a02008", "entity": {"gloss": "\u00a02008", "doc_char_end": 764, "link": "2008-12-XX", "doc_char_begin": 760}, "doc_char_end": 764, "doc_char_begin": 760, "type": {"gloss": "Date", "idx": 3, "linking": "date-picker", "name": "DATE", "icon": "fa-calendar"}}, {"gloss": "\u00a0April\u00a02009", "entity": {"gloss": "\u00a0April\u00a02009", "doc_char_end": 1300, "link": "2009-04-01", "doc_char_begin": 1290}, "doc_char_end": 1300, "doc_char_begin": 1290, "type": {"gloss": "Date", "idx": 3, "linking": "date-picker", "name": "DATE", "icon": "fa-calendar"}}, {"gloss": "\u00a0Vietnam", "entity": {"gloss": "\u00a0Vietnam", "doc_char_end": 1412, "link": "Vietnam", "doc_char_begin": 1405}, "doc_char_end": 1412, "doc_char_begin": 1405, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Laos", "entity": {"gloss": "\u00a0Laos", "doc_char_end": 1421, "link": "Laos", "doc_char_begin": 1417}, "doc_char_end": 1421, "doc_char_begin": 1417, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}, {"gloss": "\u00a0Guangxi\u00a0Zhuang\u00a0Autonomous\u00a0Region", "entity": {"gloss": "\u00a0Guangxi\u00a0Zhuang\u00a0Autonomous\u00a0Region", "doc_char_end": 1468, "link": "Guangxi", "doc_char_begin": 1436}, "doc_char_end": 1468, "doc_char_begin": 1436, "type": {"gloss": "City/State/Country", "idx": 2, "linking": "wiki-search", "name": "GPE", "icon": "fa-globe"}}]
    #"
    mentions, canonical_mentions, links, relations = parse_exhaustive_entities_response(question, response)

    assert len(mentions) == 28
    assert len(canonical_mentions) == 28
    assert len(links) == 16
    assert len(relations) == 0

    assert mentions[0].id == Provenance("NYT_ENG_20130911.0085", 101, 106)
    assert mentions[0].type == "GPE"
    assert mentions[0].gloss == "China"
    assert canonical_mentions[0].id == Provenance("NYT_ENG_20130911.0085", 101, 106)
    assert canonical_mentions[0].canonical_id == canonical_mentions[0].id
    assert links[0].id == Provenance("NYT_ENG_20130911.0085", 101, 106)
    assert links[0].link_name == "China"

# TODO: Include some awareness of timestamps
def parse_responses():
    evaluation_mentions = []
    evaluation_links = []
    evaluation_relations = []

    for row in db.pg_select("""
SELECT a.id AS assignment_id, b.id AS question_batch_id, q.id AS question_id, b.batch_type, q.params AS question, a.response AS response
FROM mturk_assignment a,
     mturk_hit h,
     evaluation_question q,
     evaluation_batch b
WHERE a.hit_id = h.id AND h.question_id = q.id AND h.question_batch_id = b.id
 AND NOT a.ignored"""): # Q: Should there be a fixed type?
        if len(row.response) == 0:
            logger.warning("Empty response : %s", row)
            continue

        question = json.loads(row.question)
        response = json.loads(row.response)

        if row.batch_type == "selective_relations":
            mentions, canonical_mentions, links, relations = parse_selective_relations_response(question, response)
        elif row.batch_type == "exhaustive_relations":
            mentions, canonical_mentions, links, relations = parse_exhaustive_relations_response(question, response)
        elif row.batch_type == "exhaustive_entities":
            mentions, canonical_mentions, links, relations = parse_exhaustive_entities_response(question, response)
        else:
            raise ValueError("Unexpected batch type: " + row.batch_type)

        assert len(mentions) == len(canonical_mentions)

        # evaluation_mention_response
        for mention, canonical_mention in zip(mentions, canonical_mentions):
            assert canonical_mention.id == mention.id
            evaluation_mentions.append(EvaluationMentionResponse(
                row.assignment_id,
                row.question_batch_id,
                row.question_id,
                mention.id.doc_id,
                mention.id,
                canonical_mention.id,
                mention.type,
                mention.gloss,
                canonical_mention.confidence,))

        # evaluation_link_response
        for link in links:
            evaluation_links.append(EvaluationLinkResponse(
                row.assignment_id,
                row.question_batch_id,
                row.question_id,
                link.id.doc_id,
                link.id,
                link.link_name,
                link.confidence,))

        for relation in relations:
            evaluation_relations.append(EvaluationRelationResponse(
                row.assignment_id,
                row.question_batch_id,
                row.question_id,
                relation.subject_id.doc_id,
                relation.subject_id,
                relation.object_id,
                relation.relation,
                relation.confidence,))


    with db.CONN:
        with db.CONN.cursor() as cur:
            db.execute_values(cur, """INSERT INTO evaluation_mention_response(assignment_id, question_batch_id, question_id, doc_id, mention_id, canonical_id, mention_type, gloss, weight) VALUES %s""", evaluation_mentions)
            db.execute_values(cur, """INSERT INTO evaluation_link_response(assignment_id, question_batch_id, question_id, doc_id, mention_id, link_name, weight) VALUES %s""", evaluation_links)
            db.execute_values(cur, """INSERT INTO evaluation_relation_response(assignment_id, question_batch_id, question_id, doc_id, subject_id, object_id, relation, weight) VALUES %s""", evaluation_relations)

