# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2021 CERN.
#
# Invenio-Vocabularies is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.


"""Example of a record API."""

from invenio_pidstore.providers.recordid_v2 import RecordIdProviderV2
from invenio_records.dumpers import SearchDumper
from invenio_records.dumpers.relations import RelationDumperExt
from invenio_records.systemfields import ConstantField, RelationsField
from invenio_records_resources.records.api import Record as RecordBase
from invenio_records_resources.records.systemfields import (
    IndexField,
    PIDField,
    PIDListRelation,
)
from invenio_vocabularies.records.api import Vocabulary

from oarepo_vocabularies_basic.records.api import OARepoVocabularyBasic
from oarepo_vocabularies.records.system_fields.pid_hierarchy_relation import PIDHierarchyRelation, \
    PIDHierarchyListRelation
from . import models


class Record(RecordBase):
    """Example bibliographic record API."""

    model_cls = models.RecordMetadata
    schema = ConstantField("$schema", "local://records/record-v1.0.0.json")
    index = IndexField("records-record-v1.0.0", search_alias="records")
    pid = PIDField("id", provider=RecordIdProviderV2)

    # Definitions of relationships from a bibliographic record to the
    # generic vocabularies.
    relations = RelationsField(
        hierarchy=PIDHierarchyRelation(
            "metadata.hierarchy",
            keys=["id", "title"],
            pid_field=OARepoVocabularyBasic.pid.with_type_ctx("hierarchy"),
            cache_key='hierarchy-relation'
        ),
        hlist=PIDHierarchyListRelation(
            "metadata.hlist",
            keys=["id", "title"],
            pid_field=OARepoVocabularyBasic.pid.with_type_ctx("hierarchy"),
            cache_key='hierarchy-relation-list'
        )
    )

    dumper = SearchDumper(
        extensions=[
            RelationDumperExt("relations"),
        ]
    )
