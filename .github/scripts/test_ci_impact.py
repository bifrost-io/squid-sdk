import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('impact', Path(__file__).with_name('ci-impact.py'))
impact = importlib.util.module_from_spec(spec)
spec.loader.exec_module(impact)
SHA='a' * 40
NEW='b' * 40

def raw(path):
    return f':100644 100644 {SHA} {NEW} M\0{path}\0'.encode()

class ImpactTests(unittest.TestCase):
    def test_docs_specs_code_and_mixed(self):
        for path in ('README.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md'):
            self.assertEqual(impact.classify([path]),'none')
        for path in ('docs/new.md','openspec/spec.md','substrate/substrate-ingest/README.md',
                     'graphql/graphql-server/src/test/schema.graphql','test/e2e-suite/src/main.ts',
                     'common/config/rush/pnpm-lock.yaml','.github/workflows/test.yml','.gitignore'):
            self.assertEqual(impact.classify([path]),'full')
        self.assertEqual(impact.classify(['README.md','src/main.ts']),'full')
    def test_pr_compares_entire_pr(self):
        with patch.object(impact.subprocess,'check_output',return_value=raw('README.md')) as git:
            self.assertEqual(impact.mode({'pull_request':{'base':{'sha':SHA}}},'pull_request'),'none')
            self.assertIn(SHA,git.call_args.args[0])
    def test_push_uses_successful_run_not_previous_failed_commit(self):
        with patch.object(impact.subprocess,'check_output',return_value=raw('src/main.ts')) as git:
            self.assertEqual(impact.mode({'before':NEW},'push',SHA),'full')
            self.assertIn(SHA,git.call_args.args[0])
            self.assertNotIn(NEW,git.call_args.args[0])
    def test_manual_rerun_first_push_missing_diff_fail_safe(self):
        self.assertEqual(impact.mode({},'workflow_dispatch',SHA),'full')
        self.assertEqual(impact.mode({},'push',SHA,'2'),'full')
        self.assertEqual(impact.mode({'before':SHA},'push'),'full')
        with patch.object(impact.subprocess,'check_output',side_effect=subprocess.CalledProcessError(1,'git')):
            self.assertEqual(impact.mode({},'push',SHA),'full')
    def test_rename_out_of_source_and_symlink_cannot_skip(self):
        for diff in (raw('docs/x.md')+raw('src/main.ts'),raw('README.md').replace(b'100644 100644',b'100644 120000')):
            with patch.object(impact.subprocess,'check_output',return_value=diff):
                self.assertEqual(impact.mode({},'push',SHA),'full')

if __name__=='__main__': unittest.main()
