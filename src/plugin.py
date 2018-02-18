#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:softtabstop=4:smarttab:expandtab

# Copyright 2017 Kevin B. Hendricks, Stratford Ontario

# This plugin's source code is available under the GNU LGPL Version 2.1 or GNU LGPL Version 3 License.
# See https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html or
# https://www.gnu.org/licenses/lgpl.html for the complete text of the license.
# If a different license is required, please contact the author directly for written permission

from __future__ import unicode_literals, division, absolute_import, print_function

import sys
import os

import zlib
import zipfile
from zipfile import ZipFile

from contextlib import contextmanager

PY3 = sys.version_info[0] == 3

# protect so that it gets to proper error message with python 2
if PY3:
    import tkinter
    import tkinter.ttk as tkinter_ttk
    import tkinter.constants as tkinter_constants
    import tkinter.filedialog as tkinter_filedialog



# convert string to utf-8
def utf8_str(p, enc='utf-8'):
    if p is None:
        return None
    if isinstance(p, str):
        return p.encode('utf-8')
    if enc != 'utf-8':
        return p.decode(enc, errors='replace').encode('utf-8')
    return p

# convert string to be unicode encoded
def unicode_str(p, enc='utf-8'):
    if p is None:
        return None
    if isinstance(p, str):
        return p
    return p.decode(enc, errors='replace')

fsencoding = sys.getfilesystemencoding()

# handle paths that might be filesystem encoded
def pathof(s, enc=fsencoding):
    if s is None:
        return None
    if isinstance(s, str):
        return s
    if isinstance(s, bytes):
        try:
            return s.decode(enc)
        except:
            pass
    return s

# properly handle relative paths as well
def relpath(path, start=None):
    return os.path.relpath(pathof(path) , pathof(start))

# generate a list of files in a folder
def walk_folder(top):
    top = pathof(top)
    rv = []
    for base, dnames, names  in os.walk(top):
        base = pathof(base)
        for name in names:
            name = pathof(name)
            rv.append(relpath(os.path.join(base, name), top))
    return rv

@contextmanager
def make_temp_directory():
    import tempfile
    import shutil
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

_SKIP_LIST = [
    'encryption.xml',
    'rights.xml',
    '.gitignore',
    '.gitattributes'
]

# check for valid source folder
def valid_source(foldpath):
    files = walk_folder(foldpath)
    for file in files:
        segs = file.split(os.sep)
        if "META-INF" in segs or "meta-inf" in segs:
            if "encryption.xml" in segs or "ENCRYPTION.XML" in segs:
                return False
    return True

# return True if file should be copied to destination folder
def valid_file_to_copy(rpath):
    segs = rpath.split(os.sep)
    if ".git" in segs:
        return False
    filename = os.path.basename(rpath)
    keep = filename not in _SKIP_LIST
    return keep


def build_epub_from_folder_contents(foldpath, epub_filepath):
    outzip = zipfile.ZipFile(pathof(epub_filepath), mode='w')
    files = walk_folder(foldpath)
    if 'mimetype' in files:
        outzip.write(pathof(os.path.join(foldpath, 'mimetype')), pathof('mimetype'), zipfile.ZIP_STORED)
        print("  loading: ", "mimetype")
    else:
        raise Exception('mimetype file is missing')
    files.remove('mimetype')
    for file in files:
        print("  loading: ", file)
        if valid_file_to_copy(file):
            filepath = os.path.join(foldpath, file)
            outzip.write(pathof(filepath),pathof(file),zipfile.ZIP_DEFLATED)
    outzip.close()


# the plugin entry point
def run(bk):

    if not PY3:
        print("This plugin requires Python 3.4 or later")
        return -1
    
    if bk.launcher_version() < 20160130:
        print("This plugin requires Sigil-0.9.3 or later")
        return -1

    # handle preferences
    prefs = bk.getPrefs() # a dictionary
    prefs.defaults['lastDir'] = os.path.expanduser('~')
    basepath = prefs['lastDir']
    if not (os.path.exists(basepath) and os.path.isdir(basepath)):
        basepath = os.path.expanduser('~')

    # ask the user to select the source folder to load files from
    localRoot = tkinter.Tk()
    localRoot.withdraw()
    if sys.platform.startswith('darwin'):
        # localRoot is is an empty topmost root window that is hidden by withdrawing it
        # but on OSX localRoot needs to be centred, and lifted and focus_force used
        # so that its child dialog will inherit focus upon launch
        localRoot.overrideredirect(True)
        # center on screen but make size 0 to hide the empty localRoot
        w = localRoot.winfo_screenwidth()
        h = localRoot.winfo_screenheight()
        x = int(w/2)
        y = int(h/2)
        localRoot.geometry('%dx%d+%d+%d' % (0, 0, x, y))
        localRoot.deiconify()
        localRoot.lift()
        localRoot.focus_force()
    foldopt = {}
    foldopt['parent'] = localRoot
    foldopt['initialdir'] = basepath
    foldopt['title'] = 'Select Folder to Input into Sigil'
    foldopt['mustexist']= True
    foldpath = tkinter_filedialog.askdirectory(**foldopt)
    # localRoot.destroy()
    localRoot.quit()

    if not foldpath:
        print("FolderIn plugin cancelled by user")
        return 0
    
    if not os.path.isdir(foldpath):
        print("Folder selected is not a directory or does not exist")
        return -1
        
    if not valid_source(foldpath):
        print("Folder selected is invalid due to existing  encryption.xml file")
        return -1
        
    # use folder name as name for epub
    epubname = os.path.basename(foldpath) + ".epub"
                
    rv = -1
    data = b''        
    with make_temp_directory() as scratchdir:
        epubpath = os.path.join(scratchdir,epubname)
        try:
            build_epub_from_folder_contents(foldpath, epubpath)
            with open(epubpath,'rb') as fp:
                data = fp.read()
            rv = 0
        except Exception as e:
            print("Import from Folder failed")
            print(str(e))
            rv = -1

    if rv == -1:
        return -1

    # add this epub to Sigil as a new ebook
    bk.addotherfile(epubname, data)

    # Save prefs to json
    prefs['lastDir'] = os.path.dirname(foldpath)
    bk.savePrefs(prefs)

    return 0

def main():
    print("I reached main when I should not have\n")
    return -1
    
if __name__ == "__main__":
    sys.exit(main())
