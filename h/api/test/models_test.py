# -*- coding: utf-8 -*-
# pylint: disable=no-self-use
import itertools
import re
import unittest
import urllib

import pytest
from mock import patch

from h.api import models

analysis = models.Annotation.__analysis__


def test_strip_scheme_char_filter():
    f = analysis['char_filter']['strip_scheme']
    p = f['pattern']
    r = f['replacement']
    assert(re.sub(p, r, 'http://ping/pong#hash') == 'ping/pong#hash')
    assert(re.sub(p, r, 'chrome-extension://1234/a.js') == '1234/a.js')
    assert(re.sub(p, r, 'a+b.c://1234/a.js') == '1234/a.js')
    assert(re.sub(p, r, 'uri:x-pdf:1234') == 'x-pdf:1234')
    assert(re.sub(p, r, 'example.com') == 'example.com')
    # This is ambiguous, and possibly cannot be expected to work.
    # assert(re.sub(p, r, 'localhost:5000') == 'localhost:5000')


def test_path_url_filter():
    patterns = analysis['filter']['path_url']['patterns']
    assert(captures(patterns, 'example.com/foo/bar?query#hash') == [
        'example.com/foo/bar'
    ])
    assert(captures(patterns, 'example.com/foo/bar/') == [
        'example.com/foo/bar/'
    ])


def test_rstrip_slash_filter():
    p = analysis['filter']['rstrip_slash']['pattern']
    r = analysis['filter']['rstrip_slash']['replacement']
    assert(re.sub(p, r, 'example.com/') == 'example.com')
    assert(re.sub(p, r, 'example.com/foo/bar/') == 'example.com/foo/bar')


def test_uri_part_tokenizer():
    text = 'http://a.b/foo/bar?c=d#stuff'
    pattern = analysis['tokenizer']['uri_part']['pattern']
    assert(re.split(pattern, text) == [
        'http', '', '', 'a', 'b', 'foo', 'bar', 'c', 'd', 'stuff'
    ])

    text = urllib.quote_plus(text)
    assert(re.split(pattern, 'http://jump.to/?u=' + text) == [
        'http', '', '', 'jump', 'to', '', 'u',
        'http', '', '', 'a', 'b', 'foo', 'bar', 'c', 'd', 'stuff'
    ])


def captures(patterns, text):
    return list(itertools.chain(*(groups(p, text) for p in patterns)))


def groups(pattern, text):
    return re.search(pattern, text).groups() or []


def test_title_with_a_document_that_has_a_title():
    annotation = models.Annotation(document={'title': 'document title'})
    assert annotation.title == 'document title'


def test_title_with_a_document_that_has_no_title():
    annotation = models.Annotation(document={})
    assert annotation.title == ''


def test_title_annotation_that_has_no_document():
    assert models.Annotation().title == ''


@pytest.mark.parametrize("input_,expected", [
    # If the annotation has both a uri and a document title it should return
    # the title linked to the uri.
    (('http://example.com/example.html', 'title'),
     '<a href="http://example.com/example.html">title</a>'),

    # If the annotation an https uri and a document title it should return the
    # title linked to the uri.
    (('https://example.com/example.html', 'title'),
     '<a href="https://example.com/example.html">title</a>'),

    # If the annotation has a document title but no uri it should just return
    # the title, not linked.
    ((None, 'title'),
     'title'),

    # If the annotation has a document title and a non-http(s) uri it should
    # just return the title, not linked.
    (('file:///home/bob/Documents/example.pdf', 'title'),
     'title'),

    # If the annotation has an http(s) uri but no document title it should
    # return the uri linked to the uri.
    (('http://example.com/example.html', None),
     '<a href="http://example.com/example.html">http://example.com/example.html</a>'),
])
def test_document_link(input_, expected):
    annotation = models.Annotation(
        uri=input_[0], document={'title': input_[1]})

    assert annotation.document_link == expected


def test_document_link_escapes_HTML_in_the_document_title():
    spam_link = '<a href="http://example.com/rubies">Buy rubies!!!</a>'
    annotation = models.Annotation(
        uri='http://example.com/example.html',
        document={'title': '</a>' + spam_link})

    assert spam_link not in annotation.document_link


def test_document_link_escapes_HTML_in_the_document_URI():
    spam_link = '<a href="http://example.com/rubies">Buy rubies!!!</a>'
    annotation = models.Annotation(
        uri='http://</a>' + spam_link,
        document={'title': 'title'})

    assert spam_link not in annotation.document_link


def test_description():
    annotation = models.Annotation(
        target=[{'selector': [{'exact': 'selected text'}]}],
        text='entered text'
    )

    assert annotation.description == (
        "&lt;blockquote&gt;selected text&lt;/blockquote&gt;entered text")


def test_created_day_string_from_annotation():
    annotation = models.Annotation(created='2015-09-04T17:37:49.517852+00:00')
    assert annotation.created_day_string == '2015-09-04'


def test_target_links_from_annotation():
    annotation = models.Annotation(target=[{'source': 'target link'}])
    assert annotation.target_links == ['target link']


def test_parent_returns_none_if_no_references():
    annotation = models.Annotation()
    assert annotation.parent is None


def test_parent_returns_none_if_empty_references():
    annotation = models.Annotation(references=[])
    assert annotation.parent is None


def test_parent_returns_none_if_references_not_list():
    annotation = models.Annotation(references={'foo': 'bar'})
    assert annotation.parent is None


@patch.object(models.Annotation, 'fetch', spec=True)
def test_parent_fetches_thread_parent(fetch):
    annotation = models.Annotation(references=['abc123', 'def456'])
    annotation.parent
    fetch.assert_called_with('def456')


@patch.object(models.Annotation, 'fetch', spec=True)
def test_parent_returns_thread_parent(fetch):
    annotation = models.Annotation(references=['abc123', 'def456'])
    parent = annotation.parent
    assert parent == fetch.return_value
