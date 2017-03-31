# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import sqlalchemy as sa
from zope.interface import implementer

from h import models
from h.formatters.interfaces import IAnnotationFormatter


@implementer(IAnnotationFormatter)
class AnnotationModerationFormatter(object):
    """
    Formatter for exposing an annotation's moderation information.

    If the passed-in user has permission to hide the annotation (if they are a
    moderator of the annotation's group, for instance), this formatter will
    add a `moderation` key to the payload, with a count of how many users have
    flagged the annotation.
    """

    def __init__(self, session, authenticated_user=None):
        self.session = session
        self.authenticated_user = authenticated_user

        # Local cache of flag counts. We don't need to care about detached
        # instances because we only store the annotation id and a boolean flag.
        self._cache = {}

    def preload(self, ids):
        if self.authenticated_user is None:
            return

        query = self.session.query(sa.func.count(models.Flag.id).label('flag_count'),
                                   models.Flag.annotation_id) \
                            .filter(models.Flag.annotation_id.in_(ids)) \
                            .group_by(models.Flag.annotation_id)

        flag_counts = {f.annotation_id: f.flag_count for f in query}
        missing_ids = set(ids) - set(flag_counts.keys())
        flag_counts.update({id_: 0 for id_ in missing_ids})

        self._cache.update(flag_counts)

    def format(self, annotation):
        # TODO: something something permissions (quite possibly not here)

        flag_count = self._load(annotation.id)
        return {'moderation': {'flag_count': flag_count} }

    def _load(self, id_):
        if self.authenticated_user is None:
            return False

        if id_ in self._cache:
            return self._cache[id_]

        flag_count = self.session.query(sa.func.count(models.Flag.id)) \
                                 .filter_by(annotation_id=id_) \
                                 .one()
        self._cache[id_] = flag_count
        return flag_count
