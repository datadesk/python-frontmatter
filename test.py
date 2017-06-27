#!/usr/bin/env python
from __future__ import unicode_literals
from __future__ import print_function

import codecs
import doctest
import glob
import json
import os
import shutil
import sys
import tempfile
import textwrap
import unittest

import six

import frontmatter
from frontmatter.default_handlers import YAMLHandler, JSONHandler, TOMLHandler 

try:
    import pyaml
except ImportError:
    pyaml = None
try:
    import toml
except ImportError:
    toml = None


class FrontmatterTest(unittest.TestCase):
    """
    Tests for parsing various kinds of content and metadata
    """
    maxDiff = None

    def test_all_the_tests(self):
        "Sanity check that everything in the tests folder loads without errors"
        for filename in glob.glob('tests/*'):
            frontmatter.load(filename)

    def test_with_markdown_content(self):
        "Parse frontmatter and only the frontmatter"
        post = frontmatter.load('tests/hello-markdown.markdown')

        metadata = {'author': 'bob', 'something': 'else', 'test': 'tester'}
        for k, v in metadata.items():
            self.assertEqual(post[k], v)

    def test_unicode_post(self):
        "Ensure unicode is parsed correctly"
        chinese = frontmatter.load('tests/chinese.txt', 'utf-8')

        self.assertTrue(isinstance(chinese.content, six.text_type))

        # this shouldn't work as ascii, because it's Hanzi
        self.assertRaises(UnicodeEncodeError, chinese.content.encode, 'ascii')

    def test_no_frontmatter(self):
        "This is not a zen exercise."
        post = frontmatter.load('tests/no-frontmatter.txt')
        with codecs.open('tests/no-frontmatter.txt', 'r', 'utf-8') as f:
            content = f.read().strip()

        self.assertEqual(post.metadata, {})
        self.assertEqual(post.content, content)

    def test_empty_frontmatter(self):
        "Frontmatter, but no metadata"
        post = frontmatter.load('tests/empty-frontmatter.txt')
        content = six.text_type("I have frontmatter but no metadata.")

        self.assertEqual(post.metadata, {})
        self.assertEqual(post.content, content)

    def test_to_dict(self):
        "Dump a post as a dict, for serializing"
        post = frontmatter.load('tests/network-diagrams.markdown')
        post_dict = post.to_dict()

        for k, v in post.metadata.items():
            self.assertEqual(post_dict[k], v)

        self.assertEqual(post_dict['content'], post.content)

    def test_to_string(self):
        "Calling str(post) returns post.content"
        post = frontmatter.load('tests/hello-world.markdown')

        # test unicode and bytes
        text = "Well, hello there, world."
        self.assertEqual(six.text_type(post), text)
        self.assertEqual(six.binary_type(post), text.encode('utf-8'))

    def test_pretty_dumping(self):
        "Use pyaml to dump nicer"
        # pyaml only runs on 2.7 and above
        if sys.version_info > (2, 6) and pyaml is not None:

            with codecs.open('tests/unpretty.md', 'r', 'utf-8') as f:
                data = f.read()

            post = frontmatter.load('tests/unpretty.md')
            yaml = pyaml.dump(post.metadata)

            # the unsafe dumper gives you nicer output, for times you want that
            dump = frontmatter.dumps(post, Dumper=pyaml.UnsafePrettyYAMLDumper)

            self.assertEqual(dump, data)
            self.assertTrue(yaml in dump)

    def test_with_crlf_string(self):
        import codecs
        markdown_bytes = b'---\r\ntitle: "my title"\r\ncontent_type: "post"\r\npublished: no\r\n---\r\n\r\nwrite your content in markdown here'
        loaded = frontmatter.loads(markdown_bytes, 'utf-8')
        self.assertEqual(loaded['title'], 'my title')

    def test_dumping_with_custom_delimiters(self):
        "dump with custom delimiters"
        post = frontmatter.load('tests/hello-world.markdown')
        dump = frontmatter.dumps(post,
            start_delimiter='+++',
            end_delimiter='+++')

        self.assertTrue('+++' in dump)

    def test_dump_to_file(self):
        "dump post to filename"
        post = frontmatter.load('tests/hello-world.markdown')

        tempdir = tempfile.mkdtemp()
        filename = os.path.join(tempdir, 'hello.md')
        frontmatter.dump(post, filename)

        with open(filename) as f:
            self.assertEqual(f.read(), frontmatter.dumps(post))

        # cleanup
        shutil.rmtree(tempdir)


class HandlerTest(unittest.TestCase):
    """
    Tests for custom handlers and formatting
    """
    def test_detect_format(self):
        "detect format based on default handlers"
        test_files = {
            'tests/hello-world.markdown': YAMLHandler, 
            'tests/hello-json.markdown': JSONHandler,
            'tests/hello-toml.markdown': TOMLHandler
        }

        for fn, Handler in test_files.items():
            with codecs.open(fn, 'r', 'utf-8') as f:
                format = frontmatter.detect_format(f.read(), frontmatter.handlers)
                self.assertIsInstance(format, Handler)

    def test_no_handler(self):
        "default to YAMLHandler when no handler is attached"
        post = frontmatter.load('tests/hello-world.markdown')
        del post.handler

        text = frontmatter.dumps(post)
        self.assertIsInstance(
            frontmatter.detect_format(text, frontmatter.handlers), 
            YAMLHandler)

    def test_custom_handler(self):
        "allow caller to specify a custom delimiter/handler"

        # not including this in the regular test directory
        # because it would/should be invalid per the defaults
        custom = textwrap.dedent("""
        ...
        dummy frontmatter
        ...
        dummy content
        """)

        # and a custom handler that really doesn't do anything
        class DummyHandler(object):
            def load(self, fm, Loader=None):
                return {'value': fm}

            def split(self, text):
                return "dummy frontmatter", "dummy content"

        # but we tell frontmatter that it is the appropriate handler
        # for the '...' delimiter
        # frontmatter.handlers['...'] = DummyHandler()
        post = frontmatter.loads(custom, handler=DummyHandler())

        self.assertEqual(post['value'], 'dummy frontmatter')

    def test_toml(self):
        "load toml frontmatter"
        if toml is None:
            return
        post = frontmatter.load('tests/hello-toml.markdown')
        metadata = {'author': 'bob', 'something': 'else', 'test': 'tester'}
        for k, v in metadata.items():
            self.assertEqual(post[k], v)

    def test_json(self):
        "load raw JSON frontmatter"
        post = frontmatter.load('tests/hello-json.markdown')
        metadata = {'author': 'bob', 'something': 'else', 'test': 'tester'}
        for k, v in metadata.items():
            self.assertEqual(post[k], v)


if __name__ == "__main__":
    doctest.testfile('README.md')
    doctest.testmod(frontmatter.default_handlers, extraglobs={'frontmatter': frontmatter})
    unittest.main()
