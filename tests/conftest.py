# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 National Library of Technology, Prague.
#
# OARepo-Vocabularies is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
# Adopted from invenio-vocabularies
#

"""Pytest configuration.

See https://pytest-invenio.readthedocs.io/ for documentation on which test
fixtures are available.
"""

# Monkey patch Werkzeug 2.1, needed to import flask_security.login_user
# Flask-Login uses the safe_str_cmp method which has been removed in Werkzeug
# 2.1. Flask-Login v0.6.0 (yet to be released at the time of writing) fixes the
# issue. Once we depend on Flask-Login v0.6.0 as the minimal version in
# Flask-Security-Invenio/Invenio-Accounts we can remove this patch again.
from invenio_records_resources.resources import RecordResource

from oarepo_vocabularies_basic.records.api import OARepoVocabularyBasic
from oarepo_vocabularies.datastreams.excel import ExcelReader
from oarepo_vocabularies.datastreams.hierarchy import HierarchyTransformer
from tests.mock_module.resources import MockResourceConfig
from tests.mock_module.services import MockService, MockServiceConfig

try:
    # Werkzeug <2.1
    from werkzeug import security

    security.safe_str_cmp
except AttributeError:
    # Werkzeug >=2.1
    import hmac

    from werkzeug import security

    security.safe_str_cmp = hmac.compare_digest

import pytest
from flask_principal import Identity, Need, UserNeed
from flask_security import login_user
from flask_security.utils import hash_password
from invenio_access.permissions import ActionUsers, any_user, system_process
from invenio_access.proxies import current_access
from invenio_accounts.proxies import current_datastore
from invenio_accounts.testutils import login_user_via_session
from invenio_app.factory import create_api as _create_api
from invenio_cache import current_cache
from invenio_vocabularies.records.api import Vocabulary
from invenio_vocabularies.records.models import VocabularyType

pytest_plugins = ("celery.contrib.pytest",)


@pytest.fixture(scope="module")
def h():
    """Accept JSON headers."""
    return {"accept": "application/json"}


@pytest.fixture(scope="module")
def extra_entry_points():
    """Extra entry points to load the mock_module features."""
    return {
        "invenio_db.models": [
            "mock_module = tests.mock_module.models",
            "mock_module_gen = mock_module_gen.records.models",
        ],
        "invenio_jsonschemas.schemas": [
            "mock_module = tests.mock_module.jsonschemas",
            "mock_module_gen = mock_module_gen.records.jsonschemas",
        ],
        "invenio_search.mappings": [
            "records = tests.mock_module.mappings",
            "mock_module_gen = mock_module_gen.records.mappings",
        ],
    }


@pytest.fixture(scope="module")
def app_config(app_config):
    """Mimic an instance's configuration."""
    app_config["JSONSCHEMAS_HOST"] = "localhost"
    app_config["BABEL_DEFAULT_LOCALE"] = "en"
    app_config["I18N_LANGUAGES"] = [("cs", "Czech")]
    app_config[
        "RECORDS_REFRESOLVER_CLS"
    ] = "invenio_records.resolver.InvenioRefResolver"
    app_config[
        "RECORDS_REFRESOLVER_STORE"
    ] = "invenio_jsonschemas.proxies.current_refresolver_store"
    app_config['VOCABULARIES_DATASTREAM_READERS'] = {
        "excel": ExcelReader,
    }
    app_config['VOCABULARIES_DATASTREAM_TRANSFORMERS'] = {
        "hierarchy": HierarchyTransformer,
    }
    return app_config


@pytest.fixture(scope="module")
def create_app(instance_path, entry_points):
    """Application factory fixture."""
    return _create_api


@pytest.fixture(scope="module")
def identity_simple():
    """Simple identity fixture."""
    i = Identity(1)
    i.provides.add(UserNeed(1))
    i.provides.add(Need(method="system_role", value="any_user"))
    return i


@pytest.fixture(scope="module")
def identity():
    """Simple identity to interact with the service."""
    i = Identity(1)
    i.provides.add(UserNeed(1))
    i.provides.add(any_user)
    i.provides.add(system_process)
    return i


@pytest.fixture(scope="module")
def basic_service(app):
    """Vocabularies service object."""
    return app.extensions["oarepo-vocabularies-basic"].service


@pytest.fixture(scope="module")
def full_service(app):
    """Vocabularies service object."""
    return app.extensions["oarepo-vocabularies-full"].service


@pytest.fixture()
def lang_type(db):
    """Get a language vocabulary type."""
    v = VocabularyType.create(id="languages", pid_type="lng")
    db.session.commit()
    return v


@pytest.fixture()
def hierarchy_type(db):
    """Get a language vocabulary type."""
    v = VocabularyType.create(id="hierarchy", pid_type="hier")
    db.session.commit()
    return v


@pytest.fixture(scope="function")
def lang_data():
    """Example data."""
    return {
        "id": "eng",
        "title": {"en": "English", "cs": "Angličtina"},
        "description": {"en": "English description", "cs": "Anglický popis"},
        "icon": "file-o",
        "type": "languages",
    }


@pytest.fixture(scope="function")
def hierarchy_data():
    ret = []
    for i in ['c', 'b', 'a']:
        for j in [None, 'c', 'b', 'a']:
            for k in [None, 'c', 'b', 'a']:
                if j is None and k is not None:
                    continue
                ret.append({
                    'id': '/'.join(x for x in (i, j, k) if x),
                    'title': {
                        'en': '-'.join(x for x in (i, j, k) if x)
                    }
                })
    return ret


@pytest.fixture(scope="function")
def hierarchy_records(clean_es, hierarchy_data, basic_service, identity, hierarchy_type):
    records = {}
    for d in hierarchy_data:
        records[d['id']] = basic_service.create(identity, {
            **d,
            'type': 'hierarchy'
        })
    return records


@pytest.fixture(scope="function")
def lang_record(clean_es, lang_data, lang_type, basic_service, identity):
    return basic_service.create(identity, lang_data)


@pytest.fixture(scope="function")
def clean_es(app, basic_service, identity):
    for rec in OARepoVocabularyBasic.index.search().scan():
        uuid = rec['uuid']
        OARepoVocabularyBasic.index.connection.delete(
            OARepoVocabularyBasic.index._name,
            uuid
        )


@pytest.fixture()
def lang_data2(lang_data):
    """Example data for testing invalid cases."""
    data = dict(lang_data)
    data["id"] = "new"
    return data


@pytest.fixture()
def example_record(db, identity, service, example_data):
    """Example record."""
    vocabulary_type_languages = VocabularyType(name="languages")
    vocabulary_type_licenses = VocabularyType(name="licenses")
    db.session.add(vocabulary_type_languages)
    db.session.add(vocabulary_type_licenses)
    db.session.commit()

    record = service.create(
        identity=identity,
        data=dict(**example_data, vocabulary_type_id=vocabulary_type_languages.id),
    )

    Vocabulary.index.refresh()  # Refresh the index
    return record


@pytest.fixture(scope="function")
def lang_data_many(lang_type, lic_type, lang_data, service, identity):
    """Create many language vocabulary."""
    lang_ids = ["fr", "tr", "gr", "ger", "es"]
    data = dict(lang_data)

    for lang_id in lang_ids:
        data["id"] = lang_id
        service.create(identity, data)
    Vocabulary.index.refresh()  # Refresh the index
    return lang_ids


@pytest.fixture()
def user(app, db):
    """Create example user."""
    with db.session.begin_nested():
        datastore = app.extensions["security"].datastore
        _user = datastore.create_user(
            email="info@inveniosoftware.org",
            password=hash_password("password"),
            active=True,
        )
    db.session.commit()
    return _user


@pytest.fixture()
def role(app, db):
    """Create some roles."""
    with db.session.begin_nested():
        datastore = app.extensions["security"].datastore
        role = datastore.create_role(name="admin", description="admin role")

    db.session.commit()
    return role


@pytest.fixture()
def client_with_credentials(db, client, user, role):
    """Log in a user to the client."""
    current_datastore.add_role_to_user(user, role)
    action = current_access.actions["superuser-access"]
    db.session.add(ActionUsers.allow(action, user_id=user.id))

    login_user(user, remember=True)
    login_user_via_session(client, email=user.email)

    return client


# FIXME: https://github.com/inveniosoftware/pytest-invenio/issues/30
# Without this, success of test depends on the tests order
@pytest.fixture()
def cache():
    """Empty cache."""
    try:
        yield current_cache
    finally:
        current_cache.clear()


@pytest.fixture()
def mock_service(app):
    return MockService(MockServiceConfig())


@pytest.fixture()
def mock_resource(mock_service, app):
    resource = RecordResource(MockResourceConfig(), mock_service)
    blueprint = resource.as_blueprint()
    app.register_blueprint(blueprint)
    return resource
