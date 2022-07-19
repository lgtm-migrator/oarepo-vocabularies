#
# Fixtures
#
import copy
from functools import partial

import pytest
from invenio_access.permissions import system_identity
from invenio_indexer.api import RecordIndexer
from invenio_search import current_search_client
from marshmallow import ValidationError

from mock_module_gen.records.api import MockModuleGenRecord
from mock_module_gen.services.schema import MockModuleGenSchema
from tests.utils import replace_timestamps


@pytest.fixture()
def mock_record(hierarchy_records):
    """An example mock record."""
    return MockModuleGenRecord.create({"title": "Test", "hierarchy": {"id": "a/b/c"}})


@pytest.fixture()
def mock_indexer():
    """Get an indexer for mock records."""
    return RecordIndexer(
        record_cls=MockModuleGenRecord,
        record_to_index=lambda r: (r.__class__.index._name, "_doc"),
    )


@pytest.fixture()
def mock_search():
    """Get a search client."""
    return partial(current_search_client.get, MockModuleGenRecord.index._name, doc_type="_doc")


#
# Tests
#
def test_mock_record(mock_record):
    """Basic smoke test."""
    assert mock_record.schema
    assert mock_record.pid


def test_linked_record(mock_record, hierarchy_records):
    """Linked record fetching."""
    # Dereference the linked language record
    hier_record = mock_record.relations.hierarchy()
    assert len(hier_record.ancestors) == 3


def test_dereferencing(mock_record):
    """Record dereferencing."""
    # Dereference the linked language record
    mock_record.relations.hierarchy.dereference()
    deferenced_lang_records = mock_record["hierarchy"]
    assert replace_timestamps(deferenced_lang_records) == [
        {
            '@v': 'VER',
            'id': 'a/b/c',
            'title': {'en': 'a-b-c'}
        },
        {
            '@v': 'VER',
            'id': 'a/b',
            'title': {'en': 'a-b'}
        },
        {
            '@v': 'VER',
            'id': 'a',
            'title': {'en': 'a'}
        }
    ]


def test_dumping(mock_record):
    """Record schema validation."""
    # Create a record linked to a language record.
    data = mock_record.dumps()
    data.pop('id')
    data.pop('pid')
    data.pop('uuid')
    assert replace_timestamps(data) == {
        '$schema': 'local://mock-module-gen-1.0.0.json',
        'created': 'TS',
        'updated': 'TS',
        'hierarchy': [
            {'@v': 'VER', 'id': 'a/b/c', 'title': {'en': 'a-b-c'}},
            {'@v': 'VER', 'id': 'a/b', 'title': {'en': 'a-b'}},
            {'@v': 'VER', 'id': 'a', 'title': {'en': 'a'}}
        ],
        'title': 'Test',
        'version_id': 1
    }


def test_indexing(mock_record, mock_indexer, mock_search):
    # Index document in ES
    assert mock_indexer.index(mock_record)["result"] == "created"

    # Retrieve document from ES and load the source
    data = mock_search(id=mock_record.id)
    record = MockModuleGenRecord.loads(data["_source"])
    record.pop('id')
    record.pop('pid')
    expected = {
        '$schema': 'local://mock-module-gen-1.0.0.json',
        'hierarchy': [
            {'@v': 'VER', 'id': 'a/b/c', 'title': {'en': 'a-b-c'}},
            {'@v': 'VER', 'id': 'a/b', 'title': {'en': 'a-b'}},
            {'@v': 'VER', 'id': 'a', 'title': {'en': 'a'}}
        ],
        'title': 'Test'
    }

    assert replace_timestamps(record) == expected

    # Dereferencing also works
    record.relations.hierarchy.dereference()

    assert replace_timestamps(record) == expected


def test_marshmallow(hierarchy_records):
    schema = MockModuleGenSchema()
    loaded = schema.load({
        'hierarchy': [
            {'@v': 'VER', 'id': 'a/b/c', 'title': {'en': 'a-b-c'}},
            {'@v': 'VER', 'id': 'a/b', 'title': {'en': 'a-b'}},
            {'@v': 'VER', 'id': 'a', 'title': {'en': 'a'}}
        ],
        'title': 'Test'
    })
    assert loaded == {
        'hierarchy': {'id': 'a/b/c'},
        'title': 'Test'
    }
    with pytest.raises(ValidationError):
        schema.load({
            'hierarchy': [
                {'@v': 'VER', 'id': 'a/b/c/d', 'title': {'en': 'a-b-c-d'}},
            ],
            'title': 'Test'
        })


def test_service_create(mock_gen_service, hierarchy_records):
    created = mock_gen_service.create(system_identity, {
        'hierarchy': 'a/b/c',
        'title': 'Test'
    })
    data = copy.deepcopy(created.data)
    data.pop('id')
    data['links'].pop('self')
    assert replace_timestamps(data) == {
        'created': 'TS',
        'links': {},
        'hierarchy': [
            {'@v': 'VER', 'id': 'a/b/c', 'title': {'en': 'a-b-c'}},
            {'@v': 'VER', 'id': 'a/b', 'title': {'en': 'a-b'}},
            {'@v': 'VER', 'id': 'a', 'title': {'en': 'a'}}
        ],
        'title': 'Test',
        'revision_id': 1,
        'updated': 'TS'
    }

    read = mock_gen_service.read(system_identity, created.id)
    data = copy.deepcopy(read.data)
    data.pop('id')
    data['links'].pop('self')
    assert replace_timestamps(data) == {
        'created': 'TS',
        'links': {},
        'hierarchy': [
            {'@v': 'VER', 'id': 'a/b/c', 'title': {'en': 'a-b-c'}},
            {'@v': 'VER', 'id': 'a/b', 'title': {'en': 'a-b'}},
            {'@v': 'VER', 'id': 'a', 'title': {'en': 'a'}}
        ],
        'title': 'Test',
        'revision_id': 1,
        'updated': 'TS'
    }
