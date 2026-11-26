import os
import unittest
from uuid import uuid4
from unittest.mock import patch
from fastapi import HTTPException
from pydantic import ValidationError

import tracked

class URLTests(unittest.TestCase):
    def test_normalization_preserves_path_and_query(self):
        self.assertEqual(tracked.normalize_url('HTTPS://Example.COM:443/a?x=1#top'),'https://example.com/a?x=1')
        self.assertNotEqual(tracked.normalize_url('https://example.com/a'),tracked.normalize_url('https://example.com/a/'))
        self.assertNotEqual(tracked.normalize_url('https://example.com/a?x=1'),tracked.normalize_url('https://example.com/a?x=2'))
    def test_bad_urls_and_extra_edit_fields_rejected(self):
        for url in ('javascript:alert(1)','https://user:pass@example.org','https://example.org:bad','https://exa mple.org','https://localhost','http://127.0.0.1','https://'+('x'*70)+'.example.org'):
            with self.assertRaises(ValueError): tracked.normalize_url(url)
        with self.assertRaises(ValidationError): tracked.EditScholarship.model_validate({'source_url':'https://example.org'})

@unittest.skipUnless(os.environ.get('POSTGRES_DB') == 'scholarship_tracker_test','requires disposable test database')
class TrackerDatabaseTests(unittest.TestCase):
    def test_save_edit_duplicate_checklist_archive(self):
        suffix=uuid4().hex
        with patch('socket.create_connection', side_effect=AssertionError('saving must not fetch a URL')):
            item=tracked.save_link(tracked.SaveLink(source_url='https://example.org/check/'+suffix+'?cycle=1#section'))
        self.assertEqual(item['status'],'saved')
        with self.assertRaises(HTTPException) as duplicate:
            tracked.save_link(tracked.SaveLink(source_url='https://EXAMPLE.org:443/check/'+suffix+'?cycle=1'))
        self.assertEqual(duplicate.exception.detail['existing_id'],item['id'])
        updated=tracked.edit_item(item['id'],tracked.EditScholarship(title='Fixture',deadline='2030-01-10',status='preparing',notes='Test note'))
        self.assertEqual(str(updated['deadline']),'2030-01-10')
        task=tracked.add_checklist(item['id'],tracked.ChecklistInput(label='Reference',due_date='2030-01-08'))
        self.assertEqual(str(task['due_date']),'2030-01-08')
        with self.assertRaises(HTTPException): tracked.edit_checklist(item['id']+999,task['id'],tracked.ChecklistEdit(completed=True))
        tracked.edit_checklist(item['id'],task['id'],tracked.ChecklistEdit(completed=True,due_date='2030-01-09'))
        saved_task=tracked.read_item(item['id'])['checklist'][0]
        self.assertTrue(saved_task['completed'])
        self.assertEqual(str(saved_task['due_date']),'2030-01-09')
        tracked.edit_checklist(item['id'],task['id'],tracked.ChecklistEdit(due_date=None))
        self.assertIsNone(tracked.read_item(item['id'])['checklist'][0]['due_date'])
        tracked.edit_item(item['id'],tracked.EditScholarship(archived=True))
        with self.assertRaises(HTTPException) as archived_duplicate:
            tracked.save_link(tracked.SaveLink(source_url='https://example.org/check/'+suffix+'?cycle=1'))
        self.assertTrue(archived_duplicate.exception.detail['archived'])
        tracked.edit_item(item['id'],tracked.EditScholarship(archived=False,status='submitted'))
        self.assertEqual(tracked.read_item(item['id'])['notes'],'Test note')

if __name__=='__main__': unittest.main()
