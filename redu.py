#!/usr/bin/env python3

import os
import json
import os.path


def size_to_human_readable(num):
    sizes = ['', 'KB', 'MB', 'GB']
    p = 0
    while num >= 1024:
        num = num / 1024.0
        p += 1
        if p >= len(sizes) - 1: break

    return '%.2f' % num + sizes[p]


class RemarkableTree:
    def __init__(self, basedir=None):
        self._raw = {}
        self._tree = {}
        self._trash = {}
        self._basedir = basedir or '/home/root/.local/share/remarkable/xochitl/'

    def _read_metadata(self, file):
        if not file.endswith('.metadata'):
            raise ValueError('not a .metadata file')
        base = file[:-len('.metadata')]

        with open(os.path.join(self._basedir, file)) as fd:
            raw = fd.read()
        data = json.loads(raw)
        parent = data['parent']
        visibleName = data['visibleName']
        docType = data['type'] # CollectionType or DocumentType

        ret = {'name': visibleName, 'parent': parent, 'type': docType, 'raw': data}
        if docType == 'DocumentType':
            ret['size'] = self._read_filesize(base)

        return ret


    def _read_filesize(self, base):
        size = 0
        for ext in ['.pdf', '.epub', '.content', '.pagedata']:
            if os.path.exists(os.path.join(self._basedir, base + ext)):
                size += os.stat(os.path.join(self._basedir, base + ext)).st_size
        return size

    def _collect_metadata(self):
        for file in os.listdir(self._basedir):
            if file.endswith('.metadata'):
                self._raw[file[:-len('.metadata')]] = self._read_metadata(file)
    
    def _create_tree(self):

        tree = {'dirs': {}, 'files': {}}
        trash = {'dirs': {}, 'files': {}}

        for name, metadata in self._raw.items():
            if metadata['type'] != 'DocumentType': continue
            path = []
            parent = metadata['parent']

            # travel up to /
            curr = tree
            while parent is not None and parent != '':
                if parent == 'trash':
                    curr = trash
                    break
                path.append(parent)
                parent = self._raw[parent]['parent']

            for p in reversed(path):
                d = self._raw[p]['name']
                if d not in curr['dirs']:
                    curr['dirs'][d] = {'dirs': {}, 'files': {}}
                curr = curr['dirs'][d]

            curr['files'][self._raw[name]['name']] = metadata

        self._tree = tree
        self._trash = trash
        return tree, trash


    @classmethod
    def _calc_tree_sizes(cls, tree):
        size_files = sum([file['size'] for file in tree['files'].values()])
        size_dirs = sum([cls._calc_tree_sizes(subtree) for subtree in tree['dirs'].values()])
        total_size = size_files + size_dirs
        tree['total_size'] = total_size
        return total_size

    def _calc_tree_size(self):
        self.__class__._calc_tree_sizes(self._tree)
        self.__class__._calc_tree_sizes(self._trash)

    def parse(self, rerun=False):
        if rerun:
            self._raw = {}

        if len(self._raw) == 0:
            self._collect_metadata()
            self._create_tree()
            self._calc_tree_size()

        return self._tree

    @classmethod
    def _print_tree(cls, tree, cols, level=0):
        files = list(tree['files'].keys())
        files.sort(key=lambda file: tree['files'][file]['size'], reverse=True)
        for file in files:
            s = '- ' * level + '@' + file + ' '
            e = size_to_human_readable(tree['files'][file]['size'])
            l = s + ' ' * (cols - len(s) - len(e)) + e
            print(l)

        dirs = list(tree['dirs'].keys())
        dirs.sort(key=lambda file: tree['dirs'][file]['total_size'], reverse=True)
        for d in dirs:
            s = '- ' * level + d + '  '
            e = size_to_human_readable(tree['dirs'][d]['total_size'])
            l = s + ' ' * (cols - len(s) - len(e)) + e
            print(l)
            cls._print_tree(tree['dirs'][d], cols, level + 1)

    def print(self):
        try:
            cols = os.get_terminal_size().columns
        except OSError:
            cols = 120
        self.__class__._print_tree(self._tree, cols=cols)


def main():
    tree = RemarkableTree()
    tree.parse()
    tree.print()


if __name__ == '__main__':
    main()
