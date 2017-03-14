"""
Definitions for the KBPO task.
"""

ner_map = {
    "PERSON": "PER",
    "ORGANIZATION": "ORG",
    "COUNTRY": "GPE",
    "LOCATION": "GPE",
    "CITY": "GPE",
    "STATE_OR_PROVINCE": "GPE",
    "GPE": "GPE",
    "TITLE": "TITLE",
    "DATE": "DATE",
    }
TYPES = list(ner_map.values())

RELATION_MAP = {
    "per:alternate_names":"per:alternate_names",

    "per:place_of_birth":"per:place_of_birth",
    "per:city_of_birth":"per:place_of_birth",
    "per:stateorprovince_of_birth":"per:place_of_birth",
    "per:country_of_birth":"per:place_of_birth",

    "per:place_of_residence":"per:place_of_residence",
    "per:cities_of_residence":"per:place_of_residence",
    "per:stateorprovinces_of_residence":"per:place_of_residence",
    "per:countries_of_residence":"per:place_of_residence",

    "per:place_of_death":"per:place_of_death",
    "per:city_of_death":"per:place_of_death",
    "per:stateorprovince_of_death":"per:place_of_death",
    "per:country_of_death":"per:place_of_death",

    "per:date_of_birth":"per:date_of_birth",
    "per:date_of_death":"per:date_of_death",
    "per:organizations_founded":"per:organizations_founded",
    "per:holds_shares_in":"per:holds_shares_in",
    "per:schools_attended":"per:schools_attended",
    "per:employee_or_member_of":"per:employee_or_member_of",
    "per:parents":"per:parents",
    "per:children":"per:children",
    "per:spouse":"per:spouse",
    "per:sibling":"per:sibling",
    "per:other_family":"per:other_family",
    "per:title":"per:title",

    "org:alternate_names":"org:alternate_names",

    "org:place_of_headquarters":"org:place_of_headquarters",
    "org:city_of_headquarters":"org:place_of_headquarters",
    "org:stateorprovince_of_headquarters":"org:place_of_headquarters",
    "org:country_of_headquarters":"org:place_of_headquarters",

    "org:date_founded":"org:date_founded",
    "org:date_dissolved":"org:date_dissolved",
    "org:founded_by":"org:founded_by",
    "org:member_of":"org:member_of",
    "org:members":"org:members",
    "org:subsidiaries":"org:subsidiaries",
    "org:parents":"org:parents",
    "org:shareholders":"org:shareholders",
    "org:holds_shares_in":"org:holds_shares_in",

    "gpe:births_in_place":"gpe:births_in_place",
    "gpe:births_in_city":"gpe:births_in_place",
    "gpe:births_in_stateorprovince":"gpe:births_in_place",
    "gpe:births_in_country":"gpe:births_in_place",

    "gpe:residents_in_place": "gpe:residents_in_place",
    "gpe:residents_in_city": "gpe:residents_in_place",
    "gpe:residents_in_stateorprovince": "gpe:residents_in_place",
    "gpe:residents_in_country": "gpe:residents_in_place",

    "gpe:deaths_in_place": "gpe:deaths_in_place",
    "gpe:deaths_in_city": "gpe:deaths_in_place",
    "gpe:deaths_in_stateorprovince": "gpe:deaths_in_place",
    "gpe:deaths_in_country": "gpe:deaths_in_place",

    "gpe:employees_or_members": "gpe:employees_or_members",
    "gpe:holds_shares_in": "gpe:holds_shares_in",
    "gpe:organizations_founded": "gpe:organizations_founded",
    "gpe:member_of": "gpe:member_of",

    "gpe:headquarters_in_place":"gpe:headquarters_in_place",
    "gpe:headquarters_in_city":"gpe:headquarters_in_place",
    "gpe:headquarters_in_stateorprovince":"gpe:headquarters_in_place",
    "gpe:headquarters_in_country":"gpe:headquarters_in_place",

    "no_relation":"no_relation",
    }
ALL_RELATIONS = list(RELATION_MAP.values())
RELATIONS = [
    "per:alternate_names",
    "per:place_of_birth",
    "per:place_of_residence",
    "per:place_of_death",
    "per:date_of_birth",
    "per:date_of_death",
    "per:organizations_founded",
    "per:holds_shares_in",
    "per:schools_attended",
    "per:employee_or_member_of",
    "per:parents",
    "per:children",
    "per:spouse",
    "per:sibling",
    "per:other_family",
    "per:title",
    "org:alternate_names",
    "org:place_of_headquarters",
    "org:date_founded",
    "org:date_dissolved",
    "org:founded_by",
    "org:member_of",
    "org:members",
    "org:subsidiaries",
    "org:parents",
    "org:shareholders",
    "org:holds_shares_in",
    "no_relation",
    ]

INVERTED_RELATIONS = {
    "per:children":["per:parents"],
    "per:other_family":["per:other_family"],
    "per:parents":["per:children"],
    "per:sibling":["per:sibling"],
    "per:spouse":["per:spouse"],
    "per:employee_or_member_of":["org:employees_or_members","gpe:employees_or_members"],
    "per:schools_attended":["org:students"],
    "per:place_of_birth":["gpe:births_in_place"],
    "per:place_of_residence":["gpe:residents_in_place"],
    "per:place_of_death":["gpe:deaths_in_place"],
    "per:organizations_founded":["org:founded_by"],
    "per:holds_shares_in":["org:shareholders"],

    "org:shareholders":["per:holds_shares_in","org:holds_shares_in","gpe:holds_shares_in"],
    "org:holds_shares_in":["org:shareholders"],
    "org:founded_by":["per:organizations_founded","org:organizations_founded","gpe:organizations_founded"],
    "org:organizations_founded":["org:founded_by",],
    "org:employees_or_members": ["per:employee_or_member_of"],
    "org:member_of":["org:members"],
    "org:members":["gpe:member_of","org:member_of"],
    "org:students":["per:schools_attended"],
    "org:subsidiaries":["org:parents"],
    "org:parents":["org:subsidiaries"],
    "org:place_of_headquarters":["gpe:headquarters_in_place"],

    "gpe:births_in_place":["per:place_of_birth"],
    "gpe:residents_in_place":["per:place_of_residence"],
    "gpe:deaths_in_place":["per:place_of_death"],
    "gpe:employees_or_members": ["per:employee_or_member_of"],
    "gpe:holds_shares_in":["org:shareholders"],
    "gpe:organizations_founded":["org:founded_by",],
    "gpe:member_of":["org:members"],
    "gpe:headquarters_in_place":["org:place_of_headquarters"],
    }
