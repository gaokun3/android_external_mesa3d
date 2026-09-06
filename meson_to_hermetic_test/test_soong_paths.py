# SPDX-License-Identifier: MIT
import tempfile
import unittest
from pathlib import Path

from meson_to_hermetic.soong_paths import sandbox_directory_inputs


class SandboxDirectoryInputsTest(unittest.TestCase):
    def test_shader_inputs_exclude_generated_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / 'src/vulkan/runtime/bvh'
            directory.mkdir(parents=True)
            for name in ('vk_bvh.h', 'leaf.h', 'leaf.spv.h'):
                (directory / name).touch()
            cmd, srcs = sandbox_directory_inputs(f'-I{directory}', [], root)
            self.assertEqual(cmd, '-I`dirname $(location src/vulkan/runtime/bvh/vk_bvh.h)`')
            self.assertIn('src/vulkan/runtime/bvh/leaf.h', srcs)
            self.assertNotIn('src/vulkan/runtime/bvh/leaf.spv.h', srcs)
            self.assertNotIn(tmp, cmd)

    def test_xml_imports_are_transitive_and_cycle_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / 'src/freedreno/registers'
            directory.mkdir(parents=True)
            for name, imported in [('a', 'b'), ('b', 'c'), ('c', 'a')]:
                (directory / f'{name}.xml').write_text(
                    f'<database xmlns="urn:test"><import file="{imported}.xml"/></database>'
                )
            _, srcs = sandbox_directory_inputs(
                f'--rnn {directory}', ['src/freedreno/registers/a.xml'], root
            )
            self.assertEqual(set(srcs), {
                f'src/freedreno/registers/{name}'
                for name in ['a.xml', 'b.xml', 'c.xml', 'gen_header.py']
            })

    def test_unknown_directory_fails_instead_of_leaking_host_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                sandbox_directory_inputs(f'-I{tmp}/unknown', [], tmp)


if __name__ == '__main__':
    unittest.main()
