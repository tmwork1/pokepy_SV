# -*- coding: utf-8 -*-
'''
画像ファイル名を日本語から数字に変換する
'''

import os
import shutil
import re
import unicodedata
import sys


def convert_dakuten(chars):
    if not type(chars) == str:
        pass
    else:
        chars = re.sub(r'\u309B','\u3099',chars)
        chars = re.sub(r'\u309C','\u309A',chars)
        return unicodedata.normalize('NFC',chars)


if len(sys.argv) < 2:
    print('!!! Incorrect Arguments !!!')
    print('python3.x encode.py <target dir> [file format]')
    exit()

dstdir = sys.argv[1]
extension = sys.argv[2] if len(sys.argv) > 2 else 'png'

filenames = os.listdir(dstdir + '/org/')
print(filenames)

with open(dstdir + '/codelist.txt', 'w', encoding='UTF-8') as f:
    i=0
    
    for filename in filenames:
        if (filename[-3:] != extension):
            continue
        
        shutil.copy(dstdir + '/org/' + filename, dstdir + '/' + str(i) + filename[-4:])
        f.write('%d\t%s\n' % (i, convert_dakuten(filename[:-4])))
        print('%d\t%s' % (i, convert_dakuten(filename[:-4])))
    
        i += 1
        