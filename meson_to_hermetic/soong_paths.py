# SPDX-License-Identifier: MIT
"""Declare directory inputs before referring to them inside Soong's sandbox."""

from pathlib import Path
import re
import xml.etree.ElementTree as ET


def sandbox_directory_inputs(cmd, srcs, source_root):
    """Translate Meson's source-directory arguments into located input paths.

    Soong copies only declared inputs into sbox. A relative source directory
    alone is therefore insufficient, even when it happens to work outside sbox.
    """
    root = Path(source_root).resolve()
    inputs = set(srcs)
    anchors = {
        'src/vulkan/runtime/bvh': ('vk_bvh.h', '*.h'),
        'src/freedreno/vulkan/bvh': ('tu_bvh.h', '*.h'),
        'src/freedreno/registers': ('gen_header.py', None),
        'src/compiler/nir': ('nir_algebraic.py', None),
        'src/util/perf': ('u_trace.py', None),
    }

    def replace(match):
        option, directory = match.groups()
        relative = Path(directory).relative_to(root).as_posix().rstrip('/')
        if relative not in anchors:
            raise ValueError(f'Undeclared Soong directory input: {relative}')
        anchor, pattern = anchors[relative]
        anchor = f'{relative}/{anchor}'
        inputs.add(anchor)
        if pattern:
            # The snapshot also contains precompiled SPIR-V headers. They are
            # outputs of these rules, not GLSL includes.
            inputs.update(
                p.relative_to(root).as_posix()
                for p in (root / relative).glob(pattern)
                if not p.name.endswith('.spv.h')
            )
        if option.startswith('--rnn'):
            # gen_header.py resolves every <import> against the register root.
            pending = [p for p in inputs if p.endswith('.xml')]
            seen = set()
            while pending:
                path = pending.pop()
                if path in seen:
                    continue
                seen.add(path)
                for element in ET.parse(root / path).iter():
                    if element.tag.rsplit('}', 1)[-1] == 'import':
                        imported = f"{relative}/{element.attrib['file']}"
                        inputs.add(imported)
                        pending.append(imported)
        return f'{option}`dirname $(location {anchor})`'

    pattern = r'(-I|--rnn\s+|-p\s+)(' + re.escape(str(root)) + r'/[^\s"`]+)'
    return re.sub(pattern, replace, cmd), sorted(inputs)
