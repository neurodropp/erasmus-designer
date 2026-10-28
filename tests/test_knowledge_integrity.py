"""Original-backed extraction and adversarial index tests; no live mutations."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import brain
import sync_lwc


def pdf_bytes(text):
    """One genuine PDF page, generated without optional Python dependencies."""
    stream=f'BT /F1 12 Tf 50 700 Td ({text}) Tj ET'.encode()
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    payload=b'%PDF-1.4\n'; offsets=[0]
    for number,body in enumerate(objects,1):
        offsets.append(len(payload)); payload+=f'{number} 0 obj\n'.encode()+body+b'\nendobj\n'
    xref=len(payload); payload+=f'xref\n0 {len(objects)+1}\n'.encode()+b'0000000000 65535 f \n'
    for offset in offsets[1:]: payload+=f'{offset:010d} 00000 n \n'.encode()
    return payload+f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode()


class OriginalBackedIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name).resolve()
        self.old_root,self.old_db=brain.ROOT,brain.DB
        self.addCleanup(self.restore_runtime)
        brain.ROOT=self.root; brain.DB=self.root/'index/evidence.sqlite'
        for folder in ('config','raw/pdf','wiki/actions'): (self.root/folder).mkdir(parents=True)
        source=dict(id='programme-2026',title='Fixture programme original',path='raw/pdf/programme.pdf',kind='programme-guide',year=2026,actions=['ALL'],sectors=['ALL'],url='https://official.example/guide.pdf')
        raw=pdf_bytes('Management maximum 20% of grant. Youth participation baseline.')
        (self.root/source['path']).write_bytes(raw); source['sha256']=hashlib.sha256(raw).hexdigest()
        route=dict(code='KA220-YOU',title='Fixture Youth',agency='AIG',sectors=['YOU'],programme_pages=[1,1],expert_pages=None,general_sources=[dict(id=source['id'],pages=[1,1],classification='fixture-context')])
        (self.root/'config/sources.json').write_text(json.dumps([source]))
        (self.root/'config/actions.json').write_text(json.dumps([route]))
        (self.root/'wiki/actions/ka220-you.md').write_text('# Fixture\n\nprogram: ERASMUS\naction: KA220-YOU\n')
        self.rebuild()
        self.meta_path=self.root/'sources/programme-2026/metadata.json'
        self.meta=json.loads(self.meta_path.read_text()); self.entry=self.meta['page_manifest'][0]
        self.immutable=self.root/self.entry['path']; self.active=self.root/self.entry['active_path']
        self.pristine=self.immutable.read_bytes()

    def restore_runtime(self):
        brain.ROOT,brain.DB=self.old_root,self.old_db; self.tmp.cleanup()

    def rebuild(self):
        with contextlib.redirect_stdout(io.StringIO()): brain.rebuild(argparse.Namespace(no_cards=True))

    def check(self):
        with contextlib.redirect_stdout(io.StringIO()): return brain.check(None)

    def show(self):
        with contextlib.redirect_stdout(io.StringIO()) as out: brain.show(argparse.Namespace(id='programme-2026:p0001'))
        return out.getvalue()

    def search(self):
        args=argparse.Namespace(year=2026,action='KA220-YOU',sector='YOU',program=None,query='Management',layer='evidence',limit=8,json=True)
        with contextlib.redirect_stdout(io.StringIO()) as out: brain.search(args)
        return json.loads(out.getvalue())

    def dossier(self):
        with contextlib.redirect_stdout(io.StringIO()) as out: brain.dossier(argparse.Namespace(year=2026,action='KA220-YOU',sector='YOU',program=None))
        return json.loads(out.getvalue())

    def corrupt_page(self): self.immutable.write_bytes(self.pristine.replace(b'20%',b'99%'))

    def assert_retrieval_blocked(self):
        self.assertEqual(self.check(),1)
        for function in (self.show,self.search,self.dossier):
            with self.assertRaisesRegex(ValueError,'Evidence integrity failed'): function()

    def test_verified_original_and_complete_digests_pass(self):
        self.assertEqual(self.check(),0); self.assertIn('20%',self.show())
        hit=self.search()['hits'][0]
        self.assertEqual(hit['derived_sha256'],hashlib.sha256(self.pristine).hexdigest())
        self.assertNotEqual(hit['sha256'],hit['derived_sha256'])
        packet=self.dossier()['evidence'][0]
        self.assertEqual(packet['derived_sha256_by_id']['programme-2026:p0001'],hit['derived_sha256'])
        self.assertTrue(packet['integrity']['original_and_derived_and_index_coherent'])

    def test_gate_readonly_api_with_explicit_root_blocks_corruption(self):
        self.assertEqual(brain.integrity_for_root(self.root),[])
        old_root=brain.ROOT; old_db=brain.DB
        self.corrupt_page()
        self.assertTrue(brain.integrity_for_root(self.root))
        self.assertEqual(brain.ROOT,old_root); self.assertEqual(brain.DB,old_db)
        self.assertFalse((self.root/'index/integrity-report.json').exists())

    def test_single_numeric_alteration_blocked_and_exact_restore_passes(self):
        self.corrupt_page(); self.assert_retrieval_blocked()
        self.immutable.write_bytes(self.pristine); self.assertEqual(self.check(),0)

    def test_active_page_alteration_blocked(self):
        self.active.write_bytes(self.pristine.replace(b'20%',b'99%')); self.assert_retrieval_blocked()

    def test_rebuild_recovers_original_bytes_instead_of_blessing_alteration(self):
        self.corrupt_page(); self.active.write_bytes(self.immutable.read_bytes())
        (self.root/self.meta['full_path']).write_text('Fake 99%')
        (self.root/'sources/programme-2026/full.md').write_text('Fake 99%')
        self.rebuild()
        self.assertEqual(self.immutable.read_bytes(),self.pristine); self.assertEqual(self.check(),0)
        self.assertNotIn('99%',self.show())
        meta=json.loads(self.meta_path.read_text())
        self.assertIn(self.entry['path'],meta['repaired_from_verified_original'])

    def test_legacy_metadata_is_refused_then_migrated_from_original(self):
        self.corrupt_page(); meta=json.loads(self.meta_path.read_text()); meta.pop('integrity_schema'); meta.pop('page_manifest')
        self.meta_path.write_text(json.dumps(meta)); self.assert_retrieval_blocked()
        self.rebuild(); self.assertEqual(self.immutable.read_bytes(),self.pristine); self.assertEqual(self.check(),0)

    def test_legacy_index_is_refused(self):
        with contextlib.closing(sqlite3.connect(brain.DB)) as con, con: con.execute('DROP TABLE index_meta')
        self.assert_retrieval_blocked(); self.rebuild(); self.assertEqual(self.check(),0)

    def test_altered_fts_body_refused_even_when_derived_files_unchanged(self):
        with contextlib.closing(sqlite3.connect(brain.DB)) as con, con: con.execute("UPDATE fts SET body=replace(body,'20%','99%') WHERE id='programme-2026:p0001'")
        self.assert_retrieval_blocked()

    def test_deleted_fts_row_refused_instead_of_false_search_miss(self):
        with contextlib.closing(sqlite3.connect(brain.DB)) as con, con: con.execute("DELETE FROM fts WHERE id='programme-2026:p0001'")
        self.assert_retrieval_blocked()

    def test_duplicate_and_orphan_fts_rows_refused(self):
        with contextlib.closing(sqlite3.connect(brain.DB)) as con, con:
            con.execute("INSERT INTO fts VALUES ('programme-2026:p0001','Fake','Management maximum 99%')")
            con.execute("INSERT INTO fts VALUES ('unlisted','Fake','Management maximum 99%')")
        self.assert_retrieval_blocked()

    def test_index_metadata_scope_alteration_refused(self):
        with contextlib.closing(sqlite3.connect(brain.DB)) as con, con:
            m=json.loads(con.execute("SELECT metadata FROM docs WHERE id='programme-2026:p0001'").fetchone()[0]); m['actions']=['ESC30']
            con.execute('UPDATE docs SET metadata=? WHERE id=?',(json.dumps(m),m['id']))
        self.assert_retrieval_blocked()

    def test_index_programme_substitution_refused(self):
        with contextlib.closing(sqlite3.connect(brain.DB)) as con, con:
            m=json.loads(con.execute("SELECT metadata FROM docs WHERE id='programme-2026:p0001'").fetchone()[0]); m['program']='ESC'
            con.execute('UPDATE docs SET metadata=? WHERE id=?',(json.dumps(m),m['id']))
        self.assert_retrieval_blocked()

    def test_full_text_alteration_refused(self):
        (self.root/self.meta['full_path']).write_text('Altered maximum 99%'); self.assert_retrieval_blocked()

    def test_page_manifest_digest_cannot_bless_changed_md_without_index_match(self):
        self.corrupt_page(); meta=json.loads(self.meta_path.read_text()); meta['page_manifest'][0]['derived_sha256']=hashlib.sha256(self.immutable.read_bytes()).hexdigest()
        self.meta_path.write_text(json.dumps(meta)); self.assert_retrieval_blocked()

    def test_catalog_change_refused_until_rebuild(self):
        routes=json.loads((self.root/'config/actions.json').read_text()); routes[0]['note']='New scope'
        (self.root/'config/actions.json').write_text(json.dumps(routes)); self.assert_retrieval_blocked()
        self.rebuild(); self.assertEqual(self.check(),0)

    def test_changed_original_rejected_before_index_replacement(self):
        old_index=brain.DB.read_bytes(); raw=self.root/'raw/pdf/programme.pdf'; raw.write_bytes(pdf_bytes('Management maximum 99%'))
        with self.assertRaisesRegex(ValueError,'trusted registry digest or changed'): self.rebuild()
        self.assertEqual(brain.DB.read_bytes(),old_index); self.assertEqual(self.immutable.read_bytes(),self.pristine)


class ReviewedDependenciesAndCitationTests(unittest.TestCase):
    def setUp(self):
        self.routes=brain.load('actions.json'); self.sources=brain.load('sources.json')

    def route(self,code): return next(a for a in self.routes if a['code']==code)

    def test_ka220_and_ka210_priorities_glossary_and_national_assessment_scope(self):
        for a in self.routes:
            if not a['code'].startswith(('KA220-','KA210-')): continue
            g=a['general_sources']; spans={(x['id'],tuple(x['pages'])) for x in g}
            self.assertIn(('programme-2026',(227,234)),spans); self.assertIn(('programme-2026',(443,456)),spans)
            if a['agency']=='EACEA':
                self.assertFalse(any(x['id'] in ('expert-2026','lump-sum-handbook-2026') for x in g))
            else:
                self.assertIn(('expert-2026',(9,14)),spans); self.assertIn(('expert-2026',(70,71)),spans)

    def test_youth_standard_and_intro_only_on_applicable_mobility_routes(self):
        for a in self.routes:
            ids={g['id'] for g in a.get('general_sources',[])}
            self.assertEqual('quality-standards-youth' in ids,a['code'] in ('KA150','KA151','KA152','KA153','KA154','KA155'))
            if a.get('program')=='ESC': self.assertTrue(all(g['id'].startswith('esc-') for g in a['general_sources']))

    def test_ka150_boundary_page_is_also_ka151(self):
        source=next(s for s in self.sources if s['id']=='programme-2026')
        self.assertEqual(self.route('KA150')['programme_pages'],[144,149])
        self.assertTrue({'KA150','KA151'}.issubset(set(brain.page_tags(source,149,self.routes)[0])))
        self.assertIn('Organisations under suspension or observation',(brain.ROOT/'sources/programme-2026/pages/page-0149.md').read_text())

    def test_other_sample_boundaries_remain_correct_and_context_restricted(self):
        source=next(s for s in self.sources if s['id']=='programme-2026')
        self.assertNotIn('KA131',brain.page_tags(source,73,self.routes)[0])
        self.assertNotIn('KA152',brain.page_tags(source,165,self.routes)[0])
        self.assertNotIn('KA153',brain.page_tags(source,180,self.routes)[0])
        priority_codes=brain.page_tags(source,227,self.routes)[0]
        self.assertIn('KA220-YOU',priority_codes); self.assertIn('KA220-SPO',priority_codes)
        self.assertNotIn('KA152',priority_codes); self.assertNotIn('ESC30',priority_codes)

    def test_real_expert_document_url_replaces_html_fragment(self):
        source=next(s for s in self.sources if s['id']=='expert-2026')
        body='[Guida esperti](../../sources/expert-2026/pages/page-0045.md)'
        result=sync_lwc.evidence_links(body,self.sources)
        self.assertIn(source['document_url']+'#page=45',result)
        self.assertNotIn('documents-and-guidelines#page=',result)
        self.assertIn('expert-2026:p0045',result)

    def test_discovery_only_pdf_uses_explicit_local_locator(self):
        source=dict(id='expert',path='raw/pdf/expert.pdf',url='https://official.example/library')
        result=sync_lwc.evidence_links('[Page](sources/expert/pages/page-0045.md)',[source])
        self.assertIn('source-expert.md',result); self.assertIn('pagina fisica 45',result)
        self.assertNotIn('#page=',result)


if __name__=='__main__': unittest.main()
