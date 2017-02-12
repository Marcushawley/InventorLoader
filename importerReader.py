#!/usr/bin/env python

"""
importerReader.py:

Simple approach to read/analyse Autodesk (R) Invetor (R) files.
"""

import sys
import os
import uuid
import datetime
import re
import zlib
import operator
import glob
import struct
from importerClasses import *
from importerUtils   import *

__author__      = 'Jens M. Plonka'
__copyright__   = 'Copyright 2017, Germany'
__version__     = '0.1.0'
__status__      = 'In-Development'

# The file the be imported
_inventor_file = None
# Indicator that everything is ready for the import
_can_import = True
# The model representing the content of the imported file
model = Inventor()

dumplinelength = 0x20

KEY_SUM_INFO_AUTHOR      = 0x04
KEY_SUM_INFO_COMMENT     = 0x06
KEY_SUM_INFO_MODIFYER    = 0x08

KEY_THUMBNAIL_1          = 0x11
KEY_THUMBNAIL_2          = 0x1C

KEY_DOC_SUM_INFO_COMPANY = 0x15

KEY_CODEPAGE             = 0x01
KEY_SET_NAME             = 0xFF
KEY_LANGUAGE_CODE        = 0x80000000

try:
	import xlrd
except:
	logError('>>>FATAL - This program requires module olefile.\nhttps://pypi.python.org/pypi/xlrd')
	_can_import = False

try:
	from xlutils.copy import copy
except:
	logError('>>>FATAL - This program requires module olefile.\nhttp://pypi.python.org/pypi/xlutils')
	_can_import = False

try:
	import xlwt
except:
	logError('>>>FATAL - This program requires module olefile.\nhttps://pypi.python.org/pypi/xlwt')
	_can_import = False

try:
	import olefile
except:
	logError('>>>FATAL - This program requires module olefile.\nhttp://www.decalage.info/python/olefileio')
	_can_import = False

def getProperty(properties, key):
	value = ''
	if (key in properties):
		value = properties[key]
		if (type(value) is str):
			if ((len(value)>0) and (value[-1] == '\0')):
				value = value[0:-1]
	return value

def getPropertySetName(properties, path):
	name = getProperty(properties, KEY_SET_NAME)

	if (len(name)==0):
		name = path[-1][1:]

	return name

def ReadInventorSummaryInformation(doc, properties, path):
	global model

	name = getPropertySetName(properties, path)

	logMessage('\t\'%s\': LC=%s)' %(name, hex(properties[KEY_LANGUAGE_CODE])))
	doc.CreatedBy = getProperty(properties, KEY_SUM_INFO_AUTHOR)
	doc.Comment = getProperty(properties, KEY_SUM_INFO_COMMENT)
	doc.LastModifiedBy = getProperty(properties, KEY_SUM_INFO_MODIFYER)

	if (name not in model.iProperties):
		model.iProperties[name] = {}

	for key in properties:
		model.iProperties[name][key] = getProperty(properties, key)
	return

def ReadInventorDocumentSummaryInformation(doc, properties, path):
	global model

	name = getPropertySetName(properties, path)

	logMessage('\t\'%s\': (LC=%s)' %(name, hex(properties[KEY_LANGUAGE_CODE])))
	doc.Company = getProperty(properties, KEY_DOC_SUM_INFO_COMPANY)

	if (name not in model.iProperties):
		model.iProperties[name] = {}

	for key in properties:
		model.iProperties[name][key] = getProperty(properties, key)
	return

def ReadOtherProperties(properties, path):
	global model

	languageCode = 1031 # en_EN

	name = getPropertySetName(properties, path)
	if (KEY_LANGUAGE_CODE in properties):
		languageCode = properties[KEY_LANGUAGE_CODE]
	logMessage('\t\'%s\': (LC = %X)' %(name, languageCode))

	props = {}

	keys = properties.keys()
	keys.sort()
	for key in keys:
		if ((key != KEY_CODEPAGE) and (key != KEY_SET_NAME) and (key != KEY_LANGUAGE_CODE)):
			val = getProperty(properties, key)
			if (type(val) is str):
				if ((key == KEY_THUMBNAIL_1) or (key == KEY_THUMBNAIL_2)):
					logMessage('\t%02X = [THUMBNAIL]' %(key))
				else:
					logMessage('\t%02X = %r' %(key, val))
			else:
				logMessage('\t%02X = %s' %(key, val))
			props[key] = val

	model.iProperties[name] = props

	return

def ReadUFRxDoc(data):
	global model

	try:
		model.UFRxDoc = UFRxDocument()
		cnt, i = getUInt16(data, 0)
		model.UFRxDoc.arr1, i = getUInt16A(data, i, cnt + 13)
		logMessage('\t[%s]' % (IntArr2Str(model.UFRxDoc.arr1, 4)))
		model.UFRxDoc.arr2, i = getUInt16A(data, i, 4)
		logMessage('\t[%s]' % (IntArr2Str(model.UFRxDoc.arr2, 4)))
		model.UFRxDoc.dat1, i = getDateTime(data, i)
		# logMessage('\t%s' %(model.UFRxDoc.dat1))
		model.UFRxDoc.arr3, i = getUInt16A(data, i, 4)
		logMessage('\t[%s]' % (IntArr2Str(model.UFRxDoc.arr3, 4)))
		model.UFRxDoc.dat2, i = getDateTime(data, i)
		# logMessage('\t%s' %(model.UFRxDoc.dat2))
		# model.UFRxDoc.txt1, i  = getLen32Text16(data, i)
		# logMessage('\t%r' %(model.UFRxDoc.txt1))
		# model.UFRxDoc.arr4, i = getUInt16A(data, i, 8)
		# logMessage('\t[%s]' % (IntArr2Str(model.UFRxDoc.arr4, 4)))
		# model.UFRxDoc.arr5, i = getUInt16A(data, i, 4)
		# logMessage('\t[%s]' % (IntArr2Str(model.UFRxDoc.arr5, 4)))
		# model.UFRxDoc.dat3, i = getDateTime(data, i)
		# # logMessage('\t%s' % (model.UFRxDoc.dat3))
		# model.UFRxDoc.revisionRef, i = getUUID(data, i, 'UFRxDoc.revisionRef')
		# # logMessage('\t%s' % (model.UFRxDoc.revisionRef))
		# model.UFRxDoc.ui1, i  = getUInt32(data, i)
		# logMessage('\t%X' % (model.UFRxDoc.ui1))
		# model.UFRxDoc.dbRef, i = getUUID(data, i, 'UFRxDoc.dbRef')
		# # logMessage('\t%s' % (model.UFRxDoc.dbRef))
		# model.UFRxDoc.txt2, i  = getLen32Text16(data, i)
		# # logMessage('\t%r' % (model.UFRxDoc.txt2))
		# model.UFRxDoc.arr6, i = getUInt16A(data, i, 3)
		# logMessage('\t[%s]' % (IntArr2Str(model.UFRxDoc.arr6, 4)))
		# cnt, i = getUInt32(data, i)
		# j = 1
		# while (j <= cnt):
		# 	txt, i = getLen32Text16(data, i)
		# 	key, i = getLen32Text16(data, i)
		# 	model.UFRxDoc.prps[key] = txt
		# 	logMessage('\t%d: %s=%r' % (j, key, txt))
		# 	j += 1
		# model.UFRxDoc.ui2, i  = getUInt32(data, i)
		# logMessage('\t\t%d' % (model.UFRxDoc.ui2))
		# model.UFRxDoc.txt3, i  = getLen32Text16(data, i)
		# logMessage('\t%r' % (model.UFRxDoc.txt3))
		# model.UFRxDoc.ui3, i  = getUInt32(data, i)
		# logMessage('\t\t%d' % (model.UFRxDoc.ui3))
		# model.UFRxDoc.arr7, i = getUInt16A(data, i, 9)
		# logMessage('\t[%s]' % (IntArr2Str(model.UFRxDoc.arr7, 4)))
		# if (model.UFRxDoc.arr7[0] == 0x17):
		# 	uid1, i =  getUUID(data, i , 'UFRxDoc.uid1')
		# 	uid2, i =  getUUID(data, i , 'UFRxDoc.uid2')
		# 	u16, i = getUInt16(data, i)
		# 	logMessage('\t%s,%s,%04X' %(uid1, uid1, u16))
		# model.UFRxDoc.arr8, i = getUInt32A(data, i, 4)
		# logMessage('\t[%s]' % (IntArr2Str(model.UFRxDoc.arr8, 4)))
		# cnt, i = getUInt32(data, i)
		# j = 1
		# while (j <= cnt):
		# 	#01 00 00 00 00 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00,'Embedding 1:{00020820-0000-0000-C000-000000000046}\',                   FF FF FF FF,'',         00 00,'',              00 00 00 00 00 00 00 00
		# 	arr1, i = getUInt32A(data, i, 5)
		# 	txt1, i = getLen32Text16(data, i)
		# 	u32, i  = getUInt32(data, i)
		# 	txt2, i = getLen32Text16(data, i)
		# 	u16, i = getUInt16(data, i)
		# 	txt3, i = getLen32Text16(data, i)
		# 	arr2, i = getUInt32A(data, i, 2)
		# 	logMessage('\t\t%d: [%s],\'%s\',%08X,\'%s\',%04X,\'%s\',[%s]' %(j, IntArr2Str(arr1, 1), txt1, u32, txt2, u16, txt3, IntArr2Str(arr2, 4)))
		# 	j += 1
		# model.UFRxDoc.arr9, i = getUInt32A(data, i, 4)
		# logMessage('\t[%s]' % (IntArr2Str(model.UFRxDoc.arr9, 4)))
		# model.UFRxDoc.arrA, i = getUInt8A(data, i, 9)
		# logMessage('\t[%s]' % (IntArr2Str(model.UFRxDoc.arrA, 2)))
		# next = True
		# while(next):
		# 	u8, i = getUInt8(data, i)
		# 	if (u8 == 0x1D):
		# 		u8, i = getUInt8(data, i)
		# 		logMessage('\t1D,%02X' % (u8))
		# 	elif ((u8 == 0) or (u8 == 1)):
		# 		i -= 1
		# 		next = False
		# 	else:
		# 		uid1, i = getUUID(data, i, 'UFRxDoc[%X].uid1' % (u8))
		# 		if ((u8 == 0x11) or (u8 == 0x13) or (u8 == 0x16) or (u8 == 0x17) or (u8 == 0x18) or (u8 == 0x1F) or (u8 == 0x24) or (u8 == 0x25)):
		# 			uid2, i = getUUID(data, i, 'UFRxDoc[%X].uid2' % (u8))
		# 			logMessage('\t%02X,%s,%s' % (u8, uid1, uid2))
		# 		else:
		# 			logMessage('\t%02X,%s' % (u8, uid1))
		# u16, i = getUInt16(data, i)
		# logMessage('\t%04X' % (u16))
		# cnt, i = getUInt32(data, i)
		# j = 1
		# while (j <= cnt):
		# 	uid3, i = getUUID(data, i, 'UFRxDoc[%d].uid3' % (j))
		# 	logMessage('\t%02X: %s' % (j, uid3))
		# 	j += 1
		# cnt, i = getUInt32(data, i)
		# j = 1
		# while (j <= cnt):
		# 	uid4, i = getUUID(data, i, 'UFRxDoc[%d].uid4' % (j))
		# 	u8a, i = getUInt8A(data, i, 11)
		# 	txt1, i = getLen32Text16(data, i)
		# 	logMessage('\t%02X: %s,[%s],\'%s\'' % (j, uid4, IntArr2Str(u8a, 2), txt1))
		# 	j += 1
	except Exception as err:
		exc_type, exc_obj, exc_tb = sys.exc_info()
		fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
		logError('>>>ERROR in %s, line %d: %s' %(fname, exc_tb.tb_lineno, err))
	return i

def ReadProtein(data):
	global _inventor_file
	size, i = getSInt32(data, 0)
	zip = data[4: size]

	folder = _inventor_file[0:-4]
	protein = open ('%s\\Protein.zip' %(folder), 'wb')
	protein.write(zip)
	protein.close()
	# logMessage('\t>>>INFO: found protein - stored as \'%s\\%s\'!' %(folder, 'Protein.zip'), Log.LOG_INFO)
	return size + 4

def ReadWorkbook(doc, data, name, stream):
	global _inventor_file

	##create a new Spreadsheet in new document
	folder = _inventor_file[0:-4]
	filename = '%s\\%s.xls' %(folder, name)

	wbk = xlrd.book.open_workbook_xls(file_contents=data, formatting_info=True)
	for name in wbk.name_obj_list:
		r = name.area2d()

	for idx in range(0, wbk.nsheets):
		sht = wbk.sheet_by_index(idx)
		rows = sht.nrows
		cols = sht.ncols
		shtName = stream + '_' + sht.name
		#TODO handle merged cells
		#TODO handle cell names
		for c in range(0, cols):
			#spreadsheet.setColumnWidth(chr(0x41+c), sht.computed_column_width(c))
			for r in range(0, rows):
				rng = '%s%d' %(chr(0x41+c), r+1)
		idx += 1

	xls = copy(wbk)
	xls.save(filename)
	# logMessage('>>>INFO - found workook: stored as %r!' %(filename), Log.LOG_INFO)
	return len(data)

def ReadRSeSegment(data, offset, idx, count):
	seg = RSeSegment()
	seg.name, i = getLen32Text16(data, offset)
	seg.ID, i = getUUID(data, i, 'RSeSegment[%d].ID'  %(idx))
	seg.revisionRef, i = getUUID(data, i, 'RSeSegment.revisionRef')
	seg.value1, i = getUInt32(data, i)
	seg.count1, i = getUInt32(data, i)
	seg.arr1, i = getUInt32A(data, i, 5) # ???, ???, ???, numSec1, ???
	seg.count2, i = getUInt32(data, i)
	seg.type, i = getLen32Text16(data, i)
	seg.arr2, i = getUInt16A(data, i, count)
	seg.objects = []
	seg.nodes = []

	logMessage('\t%s' %(seg.name))
	logMessage('\t\t[{0},{1}]'.format(seg.value1, IntArr2Str(seg.arr1,4)))
	logMessage('\t\t{0}: [{1}]'.format(seg.type, IntArr2Str(seg.arr2,4)))

	return seg, i

def ReadRSeSegmentObject(data, offset, seg, idx):
	i = offset

	obj = RSeSegmentObject()
	obj.revisionRef, i = getUUID(data, i, 'RSeSegmentType.revisionRef')
	obj.values, i = getUInt8A(data, i, 9)
	obj.segRef, i = getUUID(data, i, 'RSeSegmentType.segRef')
	obj.value1, i = getUInt32(data, i)
	obj.value2, i = getUInt32(data, i)
	seg.objects.append(obj)

	return obj, i

def ReadRSeSegmentNode(data, offset, seg, count, idx):
	i = offset

	node = RSeSegmentValue2()
	node.index, i = getUInt32(data, i)
	node.indexSegList1, i = getSInt16(data, i)
	node.indexSegList2, i = getSInt16(data, i)
	node.values, i = getUInt16A(data, i, count)
	node.number, i = getUInt16(data, i)
	seg.nodes.append(node)

	logMessage('\t\t%2X: %s' %(idx, node))

	return node, i

def ReadRSeSegmentType10(data, offset, seg):
	i = offset

	cnt = seg.count1
	idx = 0
	while (idx < cnt):
		obj, i = ReadRSeSegmentObject(data, i, seg, idx)
		idx += 1
	return i

def ReadRSeSegmentType15(data, offset, seg):
	i = offset

	cnt = seg.count1
	idx = 0
	while (idx < cnt):
		obj, i = ReadRSeSegmentObject(data, i, seg, idx)
		idx += 1

	cnt, i = getUInt32(data, i)
	idx = 1
	while (idx < cnt):
		node, i = ReadRSeSegmentNode(data, i, seg, 4, idx)
		idx += 1

	return i

def ReadRSeSegmentType1A(data, offset, seg):
	i = offset

	cnt = seg.count1
	idx = 0
	while (idx < cnt):
		obj, i = ReadRSeSegmentObject(data, i, seg, idx)
		idx += 1

	cnt, i = getUInt32(data, i)
	idx = 1
	while (idx < cnt):
		node, i = ReadRSeSegmentNode(data, i, seg, 4, idx)
		idx += 1

	return i

def ReadRSeSegmentType1D(data, offset, seg):
	i = offset

	cnt = seg.count1
	idx = 0
	while (idx < cnt):
		obj, i = ReadRSeSegmentObject(data, i, seg, idx)
		idx += 1

	cnt, i = getUInt32(data, i)
	idx = 1
	while (idx < cnt):
		node, i = ReadRSeSegmentNode(data, i, seg, 4, idx)
		idx += 1

	return i

def ReadRSeSegmentType1F(data, offset, seg):
	i = offset
	cnt2 = 0

	cnt = seg.count1
	idx = 0
	while (idx < cnt):
		obj, i = ReadRSeSegmentObject(data, i, seg, idx)
		idx += 1
		cnt2 = obj.value2

	idx = 1
	while (idx < cnt2):
		node, i = ReadRSeSegmentNode(data, i, seg, 6, idx)
		idx += 1
	return i

def ReadRSeSegInfo10(data, offset):
	global model

	model.RSeSegInfo = RSeSegInformation()

	cnt, i = getSInt32(data, offset)
	idx = 0
	while (idx < cnt):
		seg, i = ReadRSeSegment(data, i, idx, 6)

		i = ReadRSeSegmentType10(data, i, seg)

		model.RSeSegInfo.segments[seg.name] = seg

		idx += 1

	return	 i

def ReadRSeSegInfo15(data, offset):
	global model

	model.RSeSegInfo = RSeSegInformation()

	cnt, i = getSInt32(data, offset)
	idx = 0
	while (idx < cnt):
		seg, i = ReadRSeSegment(data, i, idx, 6)

		i = ReadRSeSegmentType15(data, i, seg)

		model.RSeSegInfo.segments[seg.name] = seg

		idx += 1

	model.RSeSegInfo.val, i = getUInt16A(data, i, 2)
	logMessage('\t[%s]' %(IntArr2Str(model.RSeSegInfo.val, 4)))
	cnt, i = getUInt32(data, i)
	idx = 0
	logMessage('\tList 1')
	while (idx < cnt):
		txt, i = getLen32Text16(data, i)
		logMessage('\t\t%02X: %r' % (idx, txt))
		model.RSeSegInfo.uidList1.append(txt)
		idx += 1

	cnt, i = getUInt32(data, i)
	idx = 0
	logMessage('\tList 2')
	while (idx < cnt):
		txt, i = getLen32Text16(data, i)
		logMessage('\t\t%02X: %r' % (idx, txt))
		model.RSeSegInfo.uidList2.append(txt)
		idx += 1

	return	 i

def ReadRSeSegInfo1A(data, offset):
	global model

	model.RSeSegInfo = RSeSegInformation()
	cnt, i = getSInt32(data, offset)
	idx = 0
	while (idx < cnt):
		seg, i = ReadRSeSegment(data, i, idx, 8)

		i = ReadRSeSegmentType1A(data, i, seg)

		model.RSeSegInfo.segments[seg.name] = seg

		idx += 1

	model.RSeSegInfo.val, i = getUInt16A(data, i, 2)
	logMessage('\t[%s]' %(IntArr2Str(model.RSeSegInfo.val, 4)))
	cnt, i = getUInt32(data, i)
	idx = 0
	logMessage('\tList 1')
	while (idx < cnt):
		txt, i = getLen32Text16(data, i)
		logMessage('\t\t%02X: %r' % (idx, txt))
		model.RSeSegInfo.uidList1.append(txt)
		idx += 1

	cnt, i = getUInt32(data, i)
	idx = 0
	logMessage('\tList 2')
	while (idx < cnt):
		txt, i = getLen32Text16(data, i)
		logMessage('\t\t%02X: %r' % (idx, txt))
		model.RSeSegInfo.uidList2.append(txt)
		idx += 1

	return i

def ReadRSeSegInfo1D(data):
	global model

	model.RSeSegInfo = RSeSegInformation()
	cnt, i = getSInt32(data, 0)
	idx = 0
	while (idx < cnt):
		seg, i = ReadRSeSegment(data, i, idx, 8)

		i = ReadRSeSegmentType1D(data, i, seg)

		model.RSeSegInfo.segments[seg.name] = seg

		idx += 1

	model.RSeSegInfo.val, i = getUInt16A(data, i, 2)
	logMessage('\t[%s]' %(IntArr2Str(model.RSeSegInfo.val, 4)))
	cnt, i = getUInt32(data, i)
	idx = 0
	logMessage('\tList 1')
	while (idx < cnt):
		txt, i = getLen32Text16(data, i)
		logMessage('\t\t%02X: %r' % (idx, txt))
		model.RSeSegInfo.uidList1.append(txt)
		idx += 1

	cnt, i = getUInt32(data, i)
	idx = 0
	logMessage('\tList 2')
	while (idx < cnt):
		txt, i = getLen32Text16(data, i)
		logMessage('\t\t%02X: %r' % (idx, txt))
		model.RSeSegInfo.uidList2.append(txt)
		idx += 1

	return i

def ReadRSeSegInfo1F(data):
	global model

	model.RSeSegInfo = RSeSegInformation()
	cnt, i = getSInt32(data, 0)
	idx = 0
	while (idx < cnt):
		seg, i = ReadRSeSegment(data, i, idx, 10)

		i = ReadRSeSegmentType1F(data, i, seg)

		model.RSeSegInfo.segments[seg.name] = seg

		idx += 1

	model.RSeSegInfo.val, i = getUInt16A(data, i, 2)
	logMessage('\t[%s]' %(IntArr2Str(model.RSeSegInfo.val, 4)))

	cnt, i = getUInt32(data, i)
	idx = 0
	logMessage('\tList 1')
	while (idx < cnt):
		uid, i = getUUID(data, i,'RSeSegInfo.List1[%X].uid' % idx)
		txt = getText1(uid)
		model.RSeSegInfo.uidList1.append(txt)
		logMessage('\t\t%02X: %r' % (idx, txt))
		idx += 1

	cnt, i = getUInt32(data, i)
	idx = 0
	logMessage('\tList 2')
	while (idx < cnt):
		uid, i = getUUID(data, i, 'RSeSegInfo.List2[%X].uid' % idx)
		txt = getText2(uid)
		model.RSeSegInfo.uidList2.append(txt)
		logMessage('\t\t%02X: %r' % (idx, txt))
		idx += 1

	return i

def ReadRSeDb10(data, offset):
	global model

	i = offset
	model.RSeDb.arr3, i = getUInt16A(data, i, 8)
	model.RSeDb.arr2, i = getUInt16A(data, i, 4)
	model.RSeDb.dat2, i = getDateTime(data, i)
	model.RSeDb.uid2, i = getUUID(data, i, 'RSeDb[1].uid')
	model.RSeDb.arr4, i = getUInt32A(data, i, 2)
	model.RSeDb.txt, i = getLen32Text16(data, i)
	model.RSeDb.arr5, i = getUInt32A(data, i, 6)

	logMessage('\t%r: %s' %(model.RSeDb.txt, model.RSeDb.txt2))
	logMessage('\t%s [%X]' %(model.RSeDb.uid, model.RSeDb.version))
	logMessage('\t[%s]' %(IntArr2Str(model.RSeDb.arr1, 4)))
	logMessage('\t[%s]' %(IntArr2Str(model.RSeDb.arr2, 4)))

	i = ReadRSeSegInfo10(data, i)

	return i

def ReadRSeDb15(data, offset):
	global model

	i = offset

	model.RSeDb.arr2, i = getUInt16A(data, i, 4)
	model.RSeDb.dat2, i = getDateTime(data, i)
	model.RSeDb.arr3, i = getUInt16A(data, i, 14)
	model.RSeDb.dat3, i = getDateTime(data, i)
	model.RSeDb.uid2, i = getUUID(data, i, 'RSeDb[1].uid')
	model.RSeDb.arr4, i = getUInt32A(data, i, 2)
	model.RSeDb.txt, i = getLen32Text16(data, i)
	model.RSeDb.arr5, i = getUInt32A(data, i, 6)

	logMessage('\t%r: %s' %(model.RSeDb.txt, model.RSeDb.txt2))
	logMessage('\t%s [%X]' %(model.RSeDb.uid, model.RSeDb.version))
	logMessage('\t[%s]' %(IntArr2Str(model.RSeDb.arr1, 4)))
	logMessage('\t[%s]' %(IntArr2Str(model.RSeDb.arr2, 4)))
	logMessage('\t[%s]: %s' %(IntArr2Str(model.RSeDb.arr3, 4), model.RSeDb.uid2))
	logMessage('\t[%s]' %(IntArr2Str(model.RSeDb.arr4, 4)))
	logMessage('\t[%s]' %(IntArr2Str(model.RSeDb.arr5, 4)))

	i = ReadRSeSegInfo15(data, i)

	return i

def ReadRSeDb1A(data, offset):
	global model

	i = offset

	model.RSeDb.arr2, i = getUInt16A(data, i, 4)
	model.RSeDb.dat2, i = getDateTime(data, i)
	model.RSeDb.txt2, i  = getLen32Text16(data, i)
	model.RSeDb.arr3, i = getUInt16A(data, i, 12)
	model.RSeDb.dat3, i = getDateTime(data, i)
	model.RSeDb.uid2, i = getUUID(data, i, 'RSeDb[1].uid')
	model.RSeDb.u16, i  = getUInt16(data, i)
	model.RSeDb.arr4, i = getUInt32A(data, i, 2)
	model.RSeDb.txt, i = getLen32Text16(data, i)
	model.RSeDb.arr5, i = getUInt32A(data, i, 2)
	model.RSeDb.txt3, i = getLen32Text16(data, i)
	model.RSeDb.arr6, i = getUInt32A(data, i, 4)

	logMessage('\t%r: %s' %(model.RSeDb.txt, model.RSeDb.txt2))
	logMessage('\t%s [%X]' %(model.RSeDb.uid, model.RSeDb.version))
	logMessage('\t[%s]' %(IntArr2Str(model.RSeDb.arr1, 4)))
	logMessage('\t[%s]' %(IntArr2Str(model.RSeDb.arr2, 4)))
	logMessage('\t[%s]: %s' %(IntArr2Str(model.RSeDb.arr3, 4), model.RSeDb.uid2))
	logMessage('\t%d: [%s]' %(model.RSeDb.u16, IntArr2Str(model.RSeDb.arr4, 4)))
	logMessage('\t[%s]' %(IntArr2Str(model.RSeDb.arr5, 4)))
	logMessage('\t%r' %(model.RSeDb.txt3))
	logMessage('\t[%s]' %(IntArr2Str(model.RSeDb.arr6, 4)))

	i = ReadRSeSegInfo1A(data, i)

	return i

def ReadRSeDb1D(data, offset):
	global model

	i = offset

	model.RSeDb.arr2, i = getUInt16A(data, i, 4)
	model.RSeDb.dat2, i = getDateTime(data, i)
	model.RSeDb.txt, i = getLen32Text16(data, i)

	logMessage('\t%r: %s' %(model.RSeDb.txt, model.RSeDb.txt2))
	logMessage('\t%s [%X]' %(model.RSeDb.uid, model.RSeDb.version))
	logMessage('\t[%s]' %(IntArr2Str(model.RSeDb.arr1, 4)))
	logMessage('\t[%s]' %(IntArr2Str(model.RSeDb.arr2, 4)))

	return i

def ReadRSeDb(data):
	global model

	model.RSeDb = RSeDatabase()
	i = 0
	model.RSeDb.uid, i = getUUID(data, i, 'RSeDb.uid')
	model.RSeDb.version, i = getUInt32(data, i)
	model.RSeDb.arr1, i = getUInt16A(data, i, 4)
	model.RSeDb.dat1, i = getDateTime(data, i)

	if(model.RSeDb.version == 0x10):
		i = ReadRSeDb10(data, i)
	elif(model.RSeDb.version == 0x15):
		i = ReadRSeDb15(data, i)
	elif(model.RSeDb.version == 0x1A):
		i = ReadRSeDb1A(data, i)
	elif(model.RSeDb.version == 0x1D):
		i = ReadRSeDb1D(data, i)
	elif(model.RSeDb.version == 0x1F):
		i = ReadRSeDb1D(data, i)
	else:
		logError('>>> ERROR - reading RSeDB version %X: unknown format!' %(model.RSeDb.version))

	return i

def ReadRSeDbRevisionInfo(data):
	global model

	i = 0
	key, i = getSInt32(data, i)
	model.RSeDbRevisionInfoMap = {}
	model.RSeDbRevisionInfoList = []
	cnt, i = getSInt32(data, i)
	logMessage('\tkey = %s' % (key))
	n = 0
	while (n < cnt):
		info = RSeDbRevisionInfo()
		info.ID, i = getUUID(data, i, 'RSeDbRevisionInfo.ID')
		info.value1, i = getUInt16(data, i)
		if (key == 3):
			info.value2, i = getUInt16(data, i)
		info.type, i = getUInt16(data, i)
		if (info.type == 0xFFFF):
			b, i = getUInt8(data, i)
			if (b == 0):
				info.data, i = getUInt16A(data, i, 8)
			elif (b == 1):
				info.data, i = getUInt16A(data, i, 4)
			else:
				logError('>>>ERROR - Don\'t know how to handle DbRevisionInfo.type=%02X!' % b)
		model.RSeDbRevisionInfoMap[info.ID] = info
		model.RSeDbRevisionInfoList.append(info)

		# logMessage('\t%4X: %s' % (n, info))
		n += 1
	return i

def getRevisionRef(revIdx):
	global model

	revRef = revIdx

	if ((model.RSeDbRevisionInfoList is not None) and (len(model.RSeDbRevisionInfoList) > revIdx)):
		revRef = model.RSeDbRevisionInfoList[revIdx]

	return revRef

def ReadRSeMetaDataSectionSizeArray(data, offset):
	size, i = getUInt32(data, offset)
	return i

def ReadRSeMetaDataSection1(value, data, offset, newFile):
	newFile.write('Section 1:\n')
	cnt, i = getUInt32(data, offset)
	j = 0
	while (j < cnt):
		sec = RSeStorageSection1(value)
		sec.arr, i = getUInt16A(data, i, 2)
		newFile.write('\t%02X: [%s]\n' %(j, IntArr2Str(sec.arr, 4)))
		value.sec1.append(sec)
		j += 1

	i = ReadRSeMetaDataSectionSizeArray(data, i)

	return i

def ReadRSeMetaDataSection2(value, data, offset, newFile):
	newFile.write('Section 2:\n')
	cnt, i = getUInt32(data, offset)
	n = 0
	while (n < cnt):
		sec = RSeStorageSection2(value)
		if (value.ver == 3):
			sec.revisionRef, i = getUUID(data, i, '%s.Sec2[%X].uidRef' % (value.txt2, n))
			sec.flag, i = getUInt32(data, i)
			sec.val, i = getUInt16(data, i)
			sec.arr, i = getUInt16A(data, i, 5)
		elif (value.ver == 4):
			idx, i = getUInt32(data, i)
			sec.revisionRef = getRevisionRef(idx)
			sec.flag, i = getUInt32(data, i)
			sec.val, i = getUInt16(data, i)
			sec.arr, i = getUInt16A(data, i, 5)
		else:
			idx, i = getUInt32(data, i)
			sec.revisionRef = getRevisionRef(idx)
			sec.flag, i = getUInt32(data, i)
			sec.val, i = getUInt16(data, i)
		newFile.write('\t%02X: %s\n' %(n, sec))
		value.sec2.append(sec)
		n += 1
	i = ReadRSeMetaDataSectionSizeArray(data, i)
	return i

def ReadRSeMetaDataSection3(value, data, offset, newFile):
	cnt, i = getUInt32(data, offset)
	n = 0
	newFile.write('Section 3:\n')
	while (n < cnt):
		sec = RSeStorageSection3(value)
		sec.uid, i = getUUID(data, i, '%s.Sec3[%X].uidRef' % (value.txt2, n))
		sec.arr, i = getUInt16A(data, i, 6)
		newFile.write('\t%02X: %s\n' %(n, sec))
		value.sec3.append(sec)
		n += 1
	i = ReadRSeMetaDataSectionSizeArray(data, i)
	return i

def ReadRSeMetaDataSection4Data(data, offset):
	val = RSeStorageSection4Data()
	val.num, i = getUInt16(data, offset)
	val.val, i = getUInt32(data, i)
	return val, i

def ReadRSeMetaDataSection4(value, data, offset, newFile):
	newFile.write('Section 4:\n')
	cnt, i = getUInt32(data, offset)
	n = 0
	while (n < cnt):
		sec = RSeStorageSection4(value)
		sec.uid, i = getUUID(data, i, '%s.Sec4[%X].uidRef' % (value.txt2, n))
		val, i = ReadRSeMetaDataSection4Data(data, i)
		sec.arr.append(val)
		val, i = ReadRSeMetaDataSection4Data(data, i)
		sec.arr.append(val)
		newFile.write('\t%02X: %s\n' %(n, sec))
		value.sec4.append(sec)
		n += 1
	i = ReadRSeMetaDataSectionSizeArray(data, i)
	return i

def ReadRSeMetaDataSection5(value, data, offset, newFile, size):
	newFile.write('Section 5:\n')
	#index section 4
	sec = RSeStorageSection5(value)
	sec.indexSec4, i = getUInt16A(data, offset, size / 2)

	n = 0
	m = len(sec.indexSec4)
	w = 0x10
	while (n < m):
		if (m-n >= w):
			newFile.write('\t%04X: %s\n' % (n, IntArr2Str(sec.indexSec4[n:n+w], 4)))
		else:
			newFile.write('\t%04X: %s\n' % (n, IntArr2Str(sec.indexSec4[n:m], 4)))
		n += w
	i = ReadRSeMetaDataSectionSizeArray(data, i)
	return i

def ReadRSeMetaDataSection6(value, data, offset, newFile, size, cnt):
	global dumplinelength

	sec = RSeStorageSection6(value)

	newFile.write('Section 6:\n')
	i = offset
	# ???
	# arr32, i = getUInt32A(data, i, 2)
	# n16, i = getUInt16(data, i)
	# arrU = []
	# while (n16>0)
	# 	uid, i = getUUID(data, i, '%s.Sec6[%X].uidRef' % (value.txt2, n))
	# 	arr2, i = getUInt16A(data, i, 2)
	#   arrU.append(sec7(uid, arr2))
	#   n16 -= 1
	# n16, i = getUInt16(data, i)
	# arrV = []
	# while (n16>0)
	# 	arr1, i = getUInt16A(data, i, 3)
	#	arr.append(arr1)
	j = i + size - 8
	#n16, dummy = getUInt16(data, j)
	#arr, dummy = getUInt16A(data, j + 2, 3)
	#n2, dummy = getUInt16(data, j-6)
	#sec.arr2.append(arr)
	#while ((n16 != len(sec.arr2)) or (n2 < 0x1000)):
	#	j -= 6
	#	n16, dummy = getUInt16(data, j)
	#	arr, dummy = getUInt16A(data, j + 2, 3)
	#	n2, dummy = getUInt16(data, j-6)
	#	sec.arr2.insert(0, arr)
    #
	#j -= 0x16
	#n16, dummy = getUInt16(data, j)
	#uid, dummy = getUUID(data, j + 0x02, '%s.Sec6[%X].uidRef' % (value.txt2, len(sec.arr1)))
	#u32, dummy = getUInt32(data, j + 0x12)
	#sec.arr1.append(RSeStorageSection4Data1(uid, u32))
	#while (n16 != len(sec.arr1)):
	#	j -= 0x14
	#	n16, dummy = getUInt16(data, j)
	#	uid, dummy = getUUID(data, j + 0x02, '%s.Sec6[%X].uidRef' % (value.txt2, len(sec.arr1)))
	#	u32, dummy = getUInt32(data, j + 0x12)
	#	sec.arr1.insert(0, RSeStorageSection4Data1(uid, u32))
    #
	#dumplinelength = 0x20
	#newFile.write(HexAsciiDumpAddr(data[i:j], 0, False))
	#newFile.write('\t%s\n' %(','.join(['%s' % (a) for a in sec.arr1])))
	#newFile.write('\t%s\n' %(','.join(['[%s]' % (IntArr2Str(a, 4)) for a in sec.arr2])))

	i = ReadRSeMetaDataSectionSizeArray(data, i)
	return i

def ReadRSeMetaDataSection7(value, data, offset, newFile, size, cnt):
	newFile.write('Section 7:\n')
	i = offset
	n = 0
	while (n<cnt):
		sec = RSeStorageSection7(value)
		if(size/cnt >= 0x4C):
			sec.segRef, i = getUUID(data, i, '%s.Sec7[%X].segRef' % (value.txt2, n))
			sec.revisionRef, i    = getUUID(data, i, '%s.Sec7[%X].revisionRef' % (value.txt2, n))
			sec.dbRef, i  = getUUID(data, i, '%s.Sec7[%X].dbRef' % (value.txt2, n))
			sec.txt1, i   = getLen32Text16(data, i)
			sec.arr1, i   = getUInt16A(data, i, 4)
			sec.txt2, i   = getLen32Text16(data, i)
			sec.arr2, i   = getUInt16A(data, i, 2)
			sec.txt3, i   = getLen32Text16(data, i)
			sec.arr3, i   = getUInt16A(data, i, 2)
		else:
			sec.segRef, i = getUUID(data, i, '%s.Sec7[%X].segRef' % (value.txt2, n))
			sec.revisionRef, i    = getUUID(data, i, '%s.Sec7[%X].revisionRef' % (value.txt2, n))
		newFile.write('\t%02X: %s\n' %(n, sec))
		n += 1
		value.sec7.append(sec)
	i = ReadRSeMetaDataSectionSizeArray(data, i)
	return i

def ReadRSeMetaDataSection8(value, data, offset, newFile, size, cnt):
	newFile.write('Section 8:\n')
	i = offset
	n = 0
	while (n<cnt):
		sec = RSeStorageSection8(value)
		sec.dbRevisionInfoRef, i = getUUID(data, i, '%s.Sec8[%X].dbRevisionInfoRef' % (value.txt2, n))
		sec.arr, i = getUInt16A(data, i, 2)
		newFile.write('\t%02X: %s\n' %(n, sec))
		n += 1
		value.sec8.append(sec)
	i = ReadRSeMetaDataSectionSizeArray(data, i)
	return i

def ReadRSeMetaDataSection9(value, data, offset, newFile, size, cnt):
	newFile.write('Section 9:\n')
	i = offset
	n = 0
	while (n<cnt):
		sec = RSeStorageSection9(value)
		sec.uid, i = getUUID(data, i, '%s.Sec9[%X].uidRef' % (value.txt2, n))
		sec.arr, i = getUInt8A(data, i, 3)
		newFile.write('\t%02X: %s\n' %(n, sec))
		n += 1
		value.sec9.append(sec)
	i = ReadRSeMetaDataSectionSizeArray(data, i)
	return i

def ReadRSeMetaDataSectionA(value, data, offset, newFile, size, cnt):
	"""
	Same values as in RSeSegmentType
	"""
	# newFile.write('Section 10:\n')
	i = offset
	n = 0
	while (n<cnt):
		sec = RSeStorageSectionA(value)
		sec.arr, i = getUInt16A(data, i, 4)
		# newFile.write('\t%02X: %s\n' %(n, sec))
		n += 1
		value.secA.append(sec)
	i = ReadRSeMetaDataSectionSizeArray(data, i)
	return i

def ReadRSeMetaDataSectionB(value, data, offset, newFile, size, cnt):
	newFile.write('Section 11:\n')
	i = offset
	n = 0
	while (n<cnt):
		sec = RSeStorageSectionB(value)
		sec.arr, i = getUInt16A(data, i, 2)
		newFile.write('\t%02X: %s\n' %(n, sec))
		n += 1
		value.secB.append(sec)
	return i

def ReadRSeMetaData(dataM, dataB, name):
	global model
	global _inventor_file
	global dumplinelength

	i = 0
	folder = _inventor_file[0:-4]

	value = RSeMetaData()
	value.txt1, i = getLen32Text8(dataM, i)
	value.ver, i = getUInt16(dataM, i)
	value.arr1, i = getUInt16A(dataM, i, 8)
	if (value.arr1[1] != 0):
		value.txt2, i = getLen32Text16(dataM, i)
		value.segRef, i = getUUID(dataM, i, '%s.segRef' %(value.txt2))
		value.arr2, i = getUInt32A(dataM, i, 0x3)
	else:
		value.txt2 = name
		value.segRef = None
		value.arr2 = []

	if (value.ver < 0x07):
		value.val1, i = getUInt32(dataM, i)
		value.dat1, i = getLen32Text8(dataM, i)
		value.val2, i = getUInt32(dataM, i)
		value.dat2, i = getLen32Text8(dataM, i)
	else:
		value.val1    = 0
		value.dat1, i = getLen32Text8(dataM, i)
		value.val2    = 0
		value.dat2, i = getLen32Text8(dataM, i)

	newFile = open ('%s\\%s.txt' %(folder, value.txt2), 'wb')
	newFile.write('%8X, %8X\n' %(value.val1, value.val2))
	newFile.write('\t%s\n' %(value.txt1))
	newFile.write('\t[%s]\n' %(IntArr2Str(value.arr1, 4)))
	newFile.write('\t[%s]\n' %(IntArr2Str(value.arr2, 4)))
	#newFile.write('\t%s\n' %(value.dat1))
	#newFile.write('\t%s\n' %(value.dat2))

	# dataM[i] should always be '\0x01' !!!
	x01, i = getUInt8(dataM, i)

	z = zlib.decompressobj()
	data = z.decompress(dataM[i:]+dataB)
	bak = dumplinelength
	dumplinelength = 0x30

	newFileRaw = open ('%s\\%s.bin' %(folder, value.txt2), 'wb')
	newFileRaw.write(data)
	newFileRaw.close()

	i = 0
	value.arr3, i = getUInt16A(data, i, 7)
	newFile.write('\t[%s]\n' %(IntArr2Str(value.arr3, 4)))

	i = ReadRSeMetaDataSection1(value, data, i, newFile)
	i = ReadRSeMetaDataSection2(value, data, i, newFile)
	i = ReadRSeMetaDataSection3(value, data, i, newFile)
	i = ReadRSeMetaDataSection4(value, data, i, newFile)

	l = 0x48
	i = len(data) - l - 0x18
	k = 11
	while (k > 4):
		s, j = getUInt32(data, i)
		c, j = getUInt32(data, j)
		if(c > 0):
			if(c < 0xFFFF):
				n = 0
				dumplinelength = l / c
				if (k==6):
					ReadRSeMetaDataSection6(value, data, j, newFile, l, c)
				elif (k==7):
					ReadRSeMetaDataSection7(value, data, j, newFile, l, c)
				elif (k==8):
					ReadRSeMetaDataSection8(value, data, j, newFile, l, c)
				elif (k==9):
					ReadRSeMetaDataSection9(value, data, j, newFile, l, c)
				elif (k==10):
					ReadRSeMetaDataSectionA(value, data, j, newFile, l, c)
				elif (k==11):
					ReadRSeMetaDataSectionB(value, data, j, newFile, l, c)
				else:
					newFile.write('Section %X:\n' %(k))
					newFile.write(HexAsciiDumpAddr(data[j:j+l], j, True))
			else:
				ReadRSeMetaDataSection5(value, data, j, newFile, l)
		l = s - 4
		i -= (s + 4)
		k -= 1

	value.uid2, i = getUUID(data, len(data)-0x10, '%s.uid2' % (value.txt2))
	#if (value.uid2.bytes != uuid.UUID('9744e6a4-11d1-8dd8-0008-2998bedddc09').bytes:
	# logError('>>>ERROR - STREAM CORRUPTED')
	newFile.write('\t%s\n' %(value.uid2))
	newFile.close()
	dumplinelength = bak
	model.RSeStorageData[value.txt2] = value
	# logMessage('\t>>> SEE %s\\%s.txt <<<' % (folder, value.txt2))
	return value, len(dataM)

def ReadRSeEmbeddingsDatabaseInterfaces(data):
	global model

	model.DatabaseInterfaces = {}
	i = 0
	uid1, i = getUUID(data, i, 'RSeEmbeddings.DatabaseInterfaces.uid1')
	cnt, i  = getUInt16(data, i)
	uid2, i = getUUID(data, i, 'RSeEmbeddings.DatabaseInterfaces.uid2')
	logMessage('\t%s %4X %s' % (uid1, cnt, uid2))
	n = 0
	while i < len(data):
		name, i = getLen32Text8(data, i)
		dbInterface = DbInterface(name)
		dbInterface.type, i = getSInt32(data, i)
		dbInterface.data = data[i:i+dbInterface.type]
		i += dbInterface.type
		dbInterface.uid, i = getUUID(data, i, 'RSeEmbeddings.DatabaseInterfaces[%X].uid' % (n))
		if(dbInterface.type  == 0x01):
			dbInterface.value = IFF(struct.unpack('<?', dbInterface.data)[0], 'YES', 'NO')
		elif(dbInterface.type== 0x04):
			dbInterface.value = struct.unpack('<i', dbInterface.data)[0]
		elif(dbInterface.type== 0x10):
			dbInterface.value = getUUID(dbInterface.data, 0, 'RSeEmbeddings.DatabaseInterfaces.Item.uidRef')
#		elif(dbInterface.type== 0x30):
#			dbInterface.value = getFloat64A(dbInterface.data, 0, 6)
		else:
			dbInterface.value = '[%s]' % (', '.join(['%02X' % ord(h) for h in dbInterface.data]))

		model.DatabaseInterfaces[dbInterface.name] = dbInterface
		n += 1

	# To return a new list, use the sorted() built-in function...
	for dbi in (sorted(model.DatabaseInterfaces.values(), key=operator.attrgetter('name'))):
		logMessage('\t%s' % (dbi))

	return i

def ReadRSeEmbeddingsCompObj(data):
	i = 0
	reserved1, i    = getUInt32(data, i)
	version, i      = getUInt32(data, i)
	val4, i         = getSInt32(data, i)
	clsId, i        = getUUID(data, i, 'CompObj.CLSID')
	ansiName, i     = getLen32Text8(data, i)
	ansiFmt, i      = getLen32Text8(data, i)
	ansiKey, i      = getLen32Text8(data, i)
	marker, i       = getUInt32(data, i)
	unicodeName, i  = getLen32Text8(data, i)
	unicodeFmt, i   = getLen32Text8(data, i)
	unicodeKey, i   = getLen32Text8(data, i)
	logMessage('\t%s:' %(clsId))
	logMessage('\t\t%s: %s=\'%s\'' %(ansiFmt, ansiKey, ansiName))
	logMessage('\t\t%s: %s=\'%s\'' %(unicodeFmt, unicodeKey, unicodeName))

	return i

def ReadRSeEmbeddingsContentsText16(data, offset):
	len, i = getUInt8A(data, offset, 4)
	end = i + len[3]*2
	buf = data[i: end]
	txt = buf.decode('UTF-16LE') #.encode('cp1252')
	return txt, end

def ReadRSeEmbeddingsContents(data):
	p = re.compile('\xFF\xFE\xFF.')

	arr1, i = getUInt32A(data, 0, 4)
	logMessage('\t[%s]' %IntArr2Str(arr1, 4))
	m = p.search(data, i)
	while (m):
		iOld = i
		i = m.start()
		StdoutWriteChunked(HexAsciiDumpOffset(data[iOld:i], 0))
		txt, i = ReadRSeEmbeddingsContentsText16(data, i)
		logMessage('\t%r' %(txt))
		m = p.search(data, i)

	StdoutWriteChunked(HexAsciiDumpOffset(data[i:len(data)], i))

class CDumpStream():
	def __init__(self):
		self.text = ''

	def Addline(self, line):
		if line != '':
			self.text += line + '\n'

	def Content(self):
		return self.text

def CombineHexAscii(hexDump, asciiDump):
	if hexDump == '':
		return ''
	return hexDump + '  ' + (' ' * (3 * (dumplinelength - len(asciiDump)))) + asciiDump

def HexAsciiDumpAddr(data, offset, doAscii):
	oDumpStream = CDumpStream()
	hexDump = ''
	asciiDump = ''
	for i, b in enumerate(data):
		if i % dumplinelength == 0:
			if hexDump != '':
				if (doAscii == True):
					oDumpStream.Addline(CombineHexAscii(hexDump, asciiDump))
				else:
					oDumpStream.Addline(hexDump)
			hexDump = '%04X:' % (i+offset)
			asciiDump = ''
		hexDump+= ' %02X' % ord(b)
		asciiDump += IFF(ord(b) >= 32 and ord(b), b, '.')
	if (doAscii == True):
		oDumpStream.Addline(CombineHexAscii(hexDump, asciiDump))
	else:
		oDumpStream.Addline(hexDump)
	return oDumpStream.Content()

def HexAsciiDump(data):
	return HexAsciiDumpAddr(data, 0, True)

def HexAsciiDumpOffset(data, offset):
	return HexAsciiDumpAddr(data, offset, True)

def dumpRemaining(data, offset):
	i = offset

	p1 = re.compile('\x00\x00[^\x00]\x00[^\x00]\x00[^\x00]\x00[^\x00]\x00')
	p2 = re.compile('\x00\x00\x00[ 0-z][ 0-z][ 0-z][ 0-z]')

	m1 = p1.search(data, i)
	m2 = p2.search(data, i)
	while (m1 or m2):
		iOld = i
		if (m1):
			i1 = m1.start() - 2
		else:
			i1 = len(data)
		if (m2):
			i2 = m2.start() - 1
		else:
			i2 = len(data)
		if (i1 <= i2):
			i = i1
			StdoutWriteChunked(HexAsciiDumpAddr(data[iOld:i], iOld, False))
			txt, i = getLen32Text16(data, i1)
		else:
			i = i2
			StdoutWriteChunked(HexAsciiDumpAddr(data[iOld:i], iOld, False))
			txt, i = getLen32Text8(data, i2)
		logMessage('\t%r' %(txt))
		m1 = p1.search(data, i)
		m2 = p2.search(data, i)

	StdoutWriteChunked(HexAsciiDumpAddr(data[i:len(data)], i, False))

def canImport():
	return _can_import

def getInventorFile():
	global _inventor_file
	return _inventor_file

def setInventorFile(file):
	global _inventor_file
	_inventor_file = file